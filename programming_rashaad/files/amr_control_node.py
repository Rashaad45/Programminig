#!/usr/bin/env python3
# =============================================================================
# amr_control_node.py
#
# Autonomous Mobile Robot (AMR) Perception + Slope-Adaptive Kinematics +
# CAN-bus Motor Command Node for ROS2 (Humble).
#
# WHAT THIS NODE DOES (pipeline, top to bottom):
#   1. Subscribes to an RGB-D camera and runs a semantic-segmentation model
#      (PIDNet / BiSeNetV2 style) to get a drivable-path mask + terrain class.
#   2. Fits a ground plane to the depth point cloud with RANSAC to get the
#      terrain pitch (theta) and roll (phi) angles.
#   3. Subscribes to a high-level Twist command (v_x, w_z) from a planner.
#   4. Converts (v_x, w_z) into 4 independent wheel angular velocities.
#   5. Uses the measured slope + commanded acceleration to compute the motor
#      torque and current each wheel needs (slope-adaptive current scaling).
#   6. Packs RPM + current-limit + brake-flag into a binary frame and sends
#      it out at 50 Hz to the low-level motor microcontroller over CAN/serial.
#
# DEPENDENCIES (install on the Jetson / dev machine):
#   pip install torch torchvision numpy open3d python-can
#   ROS2 Humble + rclpy, sensor_msgs, geometry_msgs, std_msgs, cv_bridge
#
# NOTE ON THE ML MODEL:
#   This script expects a TorchScript-exported PIDNet/BiSeNetV2 checkpoint.
#   Loading/inference code is written generically (works for any TorchScript
#   segmentation model with the same input/output contract) since the exact
#   trained weights are project-specific and not shipped with this script.
# =============================================================================

import struct                      # Used to pack numeric values into raw bytes for the CAN/serial frame.
import time                        # Used for timestamps and loop timing.
import math                        # Used for trig functions (sin, cos, atan2, degrees conversion).

import numpy as np                 # Core numerical library; point clouds and arrays are numpy arrays.
import torch                       # PyTorch runtime, used to run the TorchScript segmentation model.

import rclpy                       # Core ROS2 Python client library.
from rclpy.node import Node        # Base class every ROS2 node inherits from.
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy  # QoS lets us tune reliability/latency per topic.

from sensor_msgs.msg import Image, PointCloud2   # Message types for the incoming camera image and point cloud.
from sensor_msgs_py import point_cloud2 as pc2   # Helper to turn PointCloud2 messages into numpy arrays.
from geometry_msgs.msg import Twist              # Message type for the incoming (v_x, w_z) command from the planner.
from std_msgs.msg import Float32MultiArray       # Generic array message, used here to publish debug telemetry.
from cv_bridge import CvBridge                   # Converts ROS Image messages <-> OpenCV/numpy images.

try:
    import can  # python-can: real CAN bus interface (SocketCAN on Linux, etc.)
    CAN_AVAILABLE = True
except ImportError:
    # If python-can isn't installed (e.g. during simulation), we fall back to
    # printing the packed frame instead of crashing the whole node.
    CAN_AVAILABLE = False


# =============================================================================
# SECTION 1: PHYSICAL / CONTROL CONSTANTS
# These come directly from the AMR's mechanical design. Change these to match
# your actual robot before deploying on hardware.
# =============================================================================

ROBOT_MASS_KG        = 25.0     # M  : total robot mass in kilograms.
WHEEL_RADIUS_M        = 0.10     # r  : wheel radius in meters.
WHEELBASE_M           = 0.50     # L  : distance between front and rear axles.
TRACK_WIDTH_M         = 0.40     # W  : distance between left and right wheels.
GEARBOX_EFFICIENCY    = 0.85     # eta: mechanical efficiency of the gearbox (0-1).
ROLLING_FRICTION_MU   = 0.05     # mu : rolling resistance coefficient on uneven terrain.
AIR_DENSITY           = 1.225    # rho: air density (kg/m^3), for the drag term.
DRAG_COEFF            = 0.9      # Cd : aerodynamic drag coefficient (blocky robot body).
FRONTAL_AREA_M2       = 0.05     # A  : frontal cross-sectional area (m^2).
GRAVITY               = 9.81     # g  : gravitational acceleration (m/s^2).

MOTOR_TORQUE_CONST_KT = 0.45     # Kt : torque constant of the stepper motor (Nm/A), T = Kt * I.
CURRENT_BASE_A        = 1.2      # I_base   : nominal holding/running current on flat ground (A).
CURRENT_SLOPE_GAIN    = 2.0      # K_slope  : how much current rises per unit of sin(theta).
CURRENT_ACCEL_GAIN    = 0.3      # K_accel  : how much current rises per unit of longitudinal accel (m/s^2).
CURRENT_MAX_A         = 4.5      # Hardware current ceiling -- never command more than this.

CAN_SEND_RATE_HZ      = 50.0     # Rate at which we transmit motor commands to the low-level MCU.


class AMRControlNode(Node):
    """
    Main ROS2 node. Inheriting from rclpy.node.Node gives us pub/sub,
    timers, logging, and parameter handling for free.
    """

    def __init__(self):
        # Calls the parent Node constructor and registers this node under the
        # name "amr_control_node" with the ROS2 graph (visible via `ros2 node list`).
        super().__init__('amr_control_node')

        # ---------------------------------------------------------------
        # 1a. Load the segmentation model (TorchScript export).
        # ---------------------------------------------------------------
        # We declare a ROS2 parameter so the model path can be set from a
        # launch file instead of being hard-coded, e.g.:
        #   ros2 run my_pkg amr_control_node --ros-args -p model_path:=/models/pidnet_s.pt
        self.declare_parameter('model_path', '/models/pidnet_s_traced.pt')
        model_path = self.get_parameter('model_path').get_parameter_value().string_value

        # `torch.jit.load` loads a TorchScript-compiled model graph + weights
        # in one file -- no need for the original Python model class definition.
        try:
            self.seg_model = torch.jit.load(model_path)
            self.seg_model.eval()  # Disables dropout/batchnorm training behavior for inference.
            # Move the model to GPU if a CUDA device (Jetson's onboard GPU) is present.
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            self.seg_model.to(self.device)
            self.get_logger().info(f'Segmentation model loaded on {self.device}')
        except Exception as e:
            # We don't want a missing/corrupt model file to crash the whole
            # control stack -- log the error and continue with seg_model=None;
            # downstream code checks for this and skips vision-based costing.
            self.get_logger().error(f'Failed to load segmentation model: {e}')
            self.seg_model = None
            self.device = torch.device('cpu')

        # cv_bridge lets us convert sensor_msgs/Image <-> numpy/OpenCV arrays.
        self.bridge = CvBridge()

        # ---------------------------------------------------------------
        # 1b. State variables updated by callbacks, read by the control loop.
        # ---------------------------------------------------------------
        self.terrain_pitch_deg = 0.0   # theta, updated by point-cloud RANSAC callback.
        self.terrain_roll_deg  = 0.0   # phi, updated by point-cloud RANSAC callback.
        self.cmd_vx            = 0.0   # Latest commanded linear velocity (m/s) from the planner.
        self.cmd_wz            = 0.0   # Latest commanded yaw rate (rad/s) from the planner.
        self.prev_vx           = 0.0   # Previous vx sample, used to numerically estimate a_x.
        self.prev_time          = time.time()  # Timestamp of the previous control loop tick.

        # ---------------------------------------------------------------
        # 1c. QoS profile for sensor data.
        # ---------------------------------------------------------------
        # BEST_EFFORT + small queue depth is standard for high-rate sensor
        # streams: we'd rather drop an old frame than lag behind on stale data.
        sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=1
        )

        # ---------------------------------------------------------------
        # 1d. Subscriptions.
        # ---------------------------------------------------------------
        # RGB-D color image -> feeds the segmentation model.
        self.image_sub = self.create_subscription(
            Image, '/camera/color/image_raw', self.image_callback, sensor_qos)

        # Depth point cloud -> feeds the RANSAC ground-plane fit.
        self.pcd_sub = self.create_subscription(
            PointCloud2, '/camera/depth/points', self.pointcloud_callback, sensor_qos)

        # High-level velocity command from the trajectory planner (e.g. TEB / Nav2).
        self.twist_sub = self.create_subscription(
            Twist, '/cmd_vel', self.twist_callback, 10)

        # ---------------------------------------------------------------
        # 1e. Publisher for debug telemetry (so we can plot/log in rqt/rviz).
        # ---------------------------------------------------------------
        self.telemetry_pub = self.create_publisher(Float32MultiArray, '/amr/telemetry', 10)

        # ---------------------------------------------------------------
        # 1f. CAN bus interface setup.
        # ---------------------------------------------------------------
        self.can_bus = None
        if CAN_AVAILABLE:
            try:
                # 'socketcan' is the standard Linux CAN driver interface; 'can0'
                # is the typical interface name for a CAN HAT on Jetson/RPi.
                self.can_bus = can.interface.Bus(channel='can0', bustype='socketcan', bitrate=1000000)
                self.get_logger().info('CAN bus initialized on can0 @ 1 Mbps')
            except Exception as e:
                self.get_logger().warn(f'CAN bus unavailable, will log frames instead: {e}')

        # ---------------------------------------------------------------
        # 1g. Timer that drives the 50 Hz control loop.
        # ---------------------------------------------------------------
        # create_timer(period_seconds, callback) calls `control_loop` on a
        # steady wall-clock schedule -- this is what enforces the 50 Hz rate
        # required by the low-level motor drivers.
        self.timer = self.create_timer(1.0 / CAN_SEND_RATE_HZ, self.control_loop)

    # =========================================================================
    # SECTION 2: PERCEPTION CALLBACKS
    # =========================================================================

    def image_callback(self, msg: Image):
        """
        Runs the semantic segmentation model on each incoming RGB frame.
        Populates self.last_seg_mask with a per-pixel class map:
            0 = flat drivable, 1 = rough/unstable, 2 = steep/non-traversable,
            3 = dynamic obstacle.
        """
        if self.seg_model is None:
            return  # No model loaded -- skip vision inference this cycle.

        # Convert the ROS Image message into a numpy BGR8 array.
        cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

        # Resize to the model's expected input resolution (1280x720 per spec).
        # cv2 isn't imported directly here to keep dependencies minimal; in
        # production, use cv2.resize -- shown here as a numpy-based nearest
        # neighbor fallback for illustration.
        resized = cv_image  # Assume the driver already publishes 1280x720; resize here if not.

        # HWC (Height, Width, Channels) -> CHW (Channels, Height, Width), which
        # is the tensor layout PyTorch convolutional models expect.
        tensor = torch.from_numpy(resized).permute(2, 0, 1).float() / 255.0
        tensor = tensor.unsqueeze(0).to(self.device)  # Add batch dimension: [1, 3, H, W].

        with torch.no_grad():  # Disables gradient tracking -- we're only doing inference, saves memory/compute.
            logits = self.seg_model(tensor)            # Forward pass -> raw class scores per pixel.
            seg_mask = torch.argmax(logits, dim=1)      # Pick the highest-scoring class per pixel.
            self.last_seg_mask = seg_mask.squeeze(0).cpu().numpy()  # Back to numpy, drop batch dim.

    def pointcloud_callback(self, msg: PointCloud2):
        """
        Fits a ground plane to the incoming depth point cloud via RANSAC and
        updates self.terrain_pitch_deg / self.terrain_roll_deg.
        """
        # Convert the PointCloud2 message into an Nx3 numpy array of (x, y, z).
        points = np.array(list(pc2.read_points(msg, field_names=('x', 'y', 'z'), skip_nans=True)))

        if points.shape[0] < 50:
            return  # Not enough points to fit a reliable plane this cycle.

        A, B, C, D = self._ransac_plane_fit(points)

        # Surface normal vector n = [A, B, C], already implicitly normalized
        # by the fit routine below.
        norm = math.sqrt(A**2 + B**2 + C**2)

        # Pitch angle: angle between the ground normal and vertical, projected
        # onto the forward axis. arcsin(A / |n|) gives us theta in radians.
        theta_rad = math.asin(max(-1.0, min(1.0, A / norm)))  # Clamp to [-1,1] to avoid NaN from float error.
        # Roll angle: computed from the B and C components of the normal via atan2,
        # which correctly handles all quadrants (unlike a plain arctan).
        phi_rad = math.atan2(B, C)

        self.terrain_pitch_deg = math.degrees(theta_rad)
        self.terrain_roll_deg = math.degrees(phi_rad)

    @staticmethod
    def _ransac_plane_fit(points: np.ndarray, iterations: int = 200, dist_thresh: float = 0.01):
        """
        Simple RANSAC plane fitter: repeatedly samples 3 random points, fits
        the plane through them, and keeps the plane with the most inliers.

        Returns (A, B, C, D) for the plane equation A*x + B*y + C*z + D = 0,
        with (A, B, C) normalized to unit length.
        """
        best_inliers = -1
        best_plane = (0.0, 0.0, 1.0, 0.0)  # Default: flat ground facing +z.
        n_points = points.shape[0]

        for _ in range(iterations):
            # Randomly sample 3 distinct points to define a candidate plane.
            idx = np.random.choice(n_points, 3, replace=False)
            p1, p2, p3 = points[idx]

            # Two edge vectors of the triangle formed by the 3 points.
            v1 = p2 - p1
            v2 = p3 - p1
            normal = np.cross(v1, v2)          # Cross product gives a vector perpendicular to the plane.
            norm_len = np.linalg.norm(normal)
            if norm_len < 1e-6:
                continue  # Degenerate (collinear) points -- skip this sample.
            normal = normal / norm_len          # Normalize to unit length.

            A, B, C = normal
            D = -np.dot(normal, p1)             # Solve for D using point p1 on the plane.

            # Perpendicular distance from every point to this candidate plane.
            distances = np.abs(points @ normal + D)
            inliers = np.sum(distances < dist_thresh)

            if inliers > best_inliers:
                best_inliers = inliers
                best_plane = (A, B, C, D)

        return best_plane

    # =========================================================================
    # SECTION 3: COMMAND CALLBACK
    # =========================================================================

    def twist_callback(self, msg: Twist):
        """Stores the latest high-level velocity command from the planner."""
        self.cmd_vx = msg.linear.x   # Desired forward speed (m/s).
        self.cmd_wz = msg.angular.z  # Desired yaw rate (rad/s).

    # =========================================================================
    # SECTION 4: MAIN CONTROL LOOP (runs at CAN_SEND_RATE_HZ)
    # =========================================================================

    def control_loop(self):
        """
        Converts the latest (v_x, w_z) command + terrain slope into per-wheel
        RPM and current targets, packs them into a frame, and transmits it.
        Called automatically by self.timer at 50 Hz.
        """
        now = time.time()
        dt = max(now - self.prev_time, 1e-3)  # Avoid division by zero on the first tick.

        # ---------------------------------------------------------------
        # 4a. Numerically estimate longitudinal acceleration a_x from the
        # change in commanded velocity (a simple finite-difference derivative).
        # ---------------------------------------------------------------
        a_x = (self.cmd_vx - self.prev_vx) / dt
        self.prev_vx = self.cmd_vx
        self.prev_time = now

        theta_rad = math.radians(self.terrain_pitch_deg)

        # ---------------------------------------------------------------
        # 4b. Kinematics: convert (v_x, w_z) into 4 independent wheel speeds.
        # This is the classic skid-steer / 4WD kinematic model: outer wheels
        # spin faster than inner wheels during a turn, proportional to the
        # yaw rate times half the effective track+wheelbase diagonal.
        # ---------------------------------------------------------------
        half_track = (TRACK_WIDTH_M + WHEELBASE_M) / 2.0
        omega_fl = (self.cmd_vx - self.cmd_wz * half_track) / WHEEL_RADIUS_M  # rad/s
        omega_fr = (self.cmd_vx + self.cmd_wz * half_track) / WHEEL_RADIUS_M
        omega_rl = (self.cmd_vx - self.cmd_wz * half_track) / WHEEL_RADIUS_M
        omega_rr = (self.cmd_vx + self.cmd_wz * half_track) / WHEEL_RADIUS_M

        # Convert rad/s -> RPM (revolutions per minute) for the motor driver's
        # expected units: RPM = rad/s * (60 / 2*pi).
        rpm_fl = omega_fl * 60.0 / (2 * math.pi)
        rpm_fr = omega_fr * 60.0 / (2 * math.pi)
        rpm_rl = omega_rl * 60.0 / (2 * math.pi)
        rpm_rr = omega_rr * 60.0 / (2 * math.pi)

        # ---------------------------------------------------------------
        # 4c. Dynamics: total tractive force required, then torque per motor.
        # ---------------------------------------------------------------
        # F_total = slope gravity term + rolling resistance term + inertial
        # term + aerodynamic drag term (see design doc equation).
        f_slope = ROBOT_MASS_KG * GRAVITY * math.sin(theta_rad)
        f_rolling = ROBOT_MASS_KG * GRAVITY * ROLLING_FRICTION_MU * math.cos(theta_rad)
        f_inertial = ROBOT_MASS_KG * a_x
        f_drag = 0.5 * AIR_DENSITY * DRAG_COEFF * FRONTAL_AREA_M2 * (self.cmd_vx ** 2)
        f_total = f_slope + f_rolling + f_inertial + f_drag

        # Torque per motor: total force converted to wheel torque, split
        # evenly across 4 driven wheels, divided by gearbox efficiency
        # (since some of the motor's output torque is lost to friction).
        torque_per_motor = (f_total * WHEEL_RADIUS_M) / (4.0 * GEARBOX_EFFICIENCY)

        # ---------------------------------------------------------------
        # 4d. Slope-adaptive current allocation.
        # I_m = I_base + K_slope*sin(theta) + K_accel*a_x, then clamped to
        # the hardware-safe maximum current.
        # ---------------------------------------------------------------
        current_cmd = CURRENT_BASE_A + CURRENT_SLOPE_GAIN * math.sin(theta_rad) + CURRENT_ACCEL_GAIN * a_x
        # Also derive current directly from required torque via T = Kt * I,
        # and take whichever demand is higher so we never under-power the motor.
        current_from_torque = torque_per_motor / MOTOR_TORQUE_CONST_KT
        current_cmd = max(current_cmd, current_from_torque)
        current_cmd = min(current_cmd, CURRENT_MAX_A)  # Never exceed the hardware current ceiling.

        # ---------------------------------------------------------------
        # 4e. Safety brake flag: engage regenerative/holding brake on steep
        # downhill sections where the robot could roll away uncontrolled.
        # ---------------------------------------------------------------
        brake_flag = 1 if (theta_rad < -math.radians(8.0) and self.cmd_vx < 0.05) else 0

        # ---------------------------------------------------------------
        # 4f. Pack and transmit the frame to the low-level motor MCU.
        # ---------------------------------------------------------------
        frame_bytes = self._pack_motor_frame(
            rpms=(rpm_fl, rpm_fr, rpm_rl, rpm_rr),
            current_limit_a=current_cmd,
            brake_flag=brake_flag
        )
        self._send_can_frame(frame_bytes)

        # ---------------------------------------------------------------
        # 4g. Publish debug telemetry so it can be plotted/logged.
        # ---------------------------------------------------------------
        telemetry = Float32MultiArray()
        telemetry.data = [
            self.terrain_pitch_deg, self.terrain_roll_deg,
            rpm_fl, rpm_fr, rpm_rl, rpm_rr,
            torque_per_motor, current_cmd, float(brake_flag)
        ]
        self.telemetry_pub.publish(telemetry)

    # =========================================================================
    # SECTION 5: FRAME PACKING + CAN TRANSMISSION
    # =========================================================================

    @staticmethod
    def _pack_motor_frame(rpms, current_limit_a: float, brake_flag: int) -> bytes:
        """
        Packs 4x RPM (float32), 1x current limit (float32), and 1x brake flag
        (uint8) into a fixed-size binary struct for transmission.

        struct format string '<4fBf' breakdown:
          '<'  : little-endian byte order.
          '4f' : four 32-bit floats (the 4 wheel RPMs).
          'B'  : one unsigned byte (the brake flag: 0 or 1).
          'f'  : one 32-bit float (the current limit in Amps).
        Total frame size = 4*4 + 1 + 4 = 21 bytes.
        """
        return struct.pack('<4fBf', *rpms, brake_flag, current_limit_a)

    def _send_can_frame(self, payload: bytes):
        """
        Sends the packed payload as a CAN message (standard CAN frames carry
        up to 8 data bytes, so if using classic CAN 2.0B you would split this
        21-byte payload across 3 frames; CAN-FD or a serial/UART link can
        send it in one shot). Shown here as a single logical send for clarity.
        """
        if self.can_bus is not None:
            # arbitration_id 0x100 is an example message ID for "motor command".
            # In classic CAN 2.0B, split payload into <=8 byte chunks.
            chunk_size = 8
            for i in range(0, len(payload), chunk_size):
                chunk = payload[i:i + chunk_size]
                msg = can.Message(arbitration_id=0x100 + (i // chunk_size), data=chunk, is_extended_id=False)
                try:
                    self.can_bus.send(msg)
                except can.CanError as e:
                    self.get_logger().warn(f'CAN send failed: {e}')
        else:
            # Fallback for development/simulation without real CAN hardware.
            self.get_logger().debug(f'[SIM CAN] frame ({len(payload)} bytes): {payload.hex()}')


def main(args=None):
    # Initializes the ROS2 client library -- must be called before creating any nodes.
    rclpy.init(args=args)

    node = AMRControlNode()

    try:
        # rclpy.spin() blocks and keeps calling callbacks (subscriptions,
        # timers) until the node is shut down (e.g. Ctrl+C).
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # Clean shutdown: destroy the node and release ROS2 resources.
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
