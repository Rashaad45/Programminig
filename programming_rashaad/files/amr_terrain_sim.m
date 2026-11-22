%% amr_terrain_sim.m
% =========================================================================
% Full dynamic simulation of a 4-Wheel Independent Drive AMR traversing
% steep, unbalanced terrain, with slope-adaptive torque/current control.
% MATLAB R2024a compatible. No toolboxes required beyond base MATLAB.
%
% This script is the *executable, testable* counterpart to a Simulink
% block diagram: every block in the architecture (terrain model, planner,
% torque allocator, motor current model) is written here as a clearly
% separated section/function, so it can be translated 1:1 into Simulink
% Subsystem blocks later (see the accompanying documentation for the
% block-by-block Simulink layout).
%
% Sections:
%   1. Terrain generation
%   2. Robot + controller parameters
%   3. Reference path + Stanley controller
%   4. Main simulation loop (kinematics, load transfer, torque, current)
%   5. Four-panel visualization
% =========================================================================

clear; clc; close all;

%% ---------------------------------------------------------------------
% SECTION 1: TERRAIN GENERATION
% Builds a synthetic 1D terrain height profile along the travel direction
% x, with: flat ground -> smooth transition -> 20-degree incline -> uneven
% surface. This height profile is what the "terrain" would be inside a
% Simulink "Terrain Height Lookup" block (e.g. a 1-D Lookup Table block
% driven by the vehicle's current x position).
% ------------------------------------------------------------------------
x_terrain = linspace(0, 40, 4000);      % 40 m course, sampled at 1 cm resolution.
z_terrain = zeros(size(x_terrain));      % Preallocate height array.

flat_end        = 10;   % [m] end of the initial flat section.
transition_end  = 15;   % [m] end of the smooth ramp-up transition.
incline_end     = 30;   % [m] end of the 20-degree incline.
incline_deg     = 20;   % [deg] slope of the incline section.

for i = 1:length(x_terrain)
    xi = x_terrain(i);
    if xi <= flat_end
        z_terrain(i) = 0;  % Flat: height stays at 0.
    elseif xi <= transition_end
        % Smooth cosine-based transition from flat (0 slope) into the
        % incline, so there is no discontinuous slope change (which would
        % be physically unrealistic and would break the controller).
        frac = (xi - flat_end) / (transition_end - flat_end);
        smooth_frac = (1 - cos(frac * pi)) / 2;  % Eased 0->1 ramp.
        z_terrain(i) = smooth_frac * (transition_end - flat_end) * tand(incline_deg);
    elseif xi <= incline_end
        % Constant 20-degree incline: height rises linearly with x.
        z_terrain(i) = z_terrain(find(x_terrain <= transition_end, 1, 'last')) + ...
                       (xi - transition_end) * tand(incline_deg);
    else
        % Uneven surface: incline height plus pseudo-random bumps
        % (sum of sinusoids at different frequencies mimics rough ground).
        base_height = z_terrain(find(x_terrain <= incline_end, 1, 'last'));
        bump = 0.03*sin(2*pi*xi/0.8) + 0.015*sin(2*pi*xi/0.3 + 1.2);
        z_terrain(i) = base_height + bump;
    end
end

% Local terrain slope (theta) at every x, via numerical gradient (dz/dx).
% This is the same quantity Tier-1 perception in the real robot would
% estimate from the point-cloud RANSAC fit instead of a lookup table.
slope_terrain_rad = atan(gradient(z_terrain, x_terrain));

%% ---------------------------------------------------------------------
% SECTION 2: ROBOT + CONTROLLER PARAMETERS
% ------------------------------------------------------------------------
M   = 25.0;    % [kg]   Robot mass.
L   = 0.5;     % [m]    Wheelbase (front-to-rear axle distance).
W   = 0.4;     % [m]    Track width (left-to-right wheel distance).
r   = 0.1;     % [m]    Wheel radius.
Kt  = 0.45;    % [Nm/A] Motor torque constant.
g   = 9.81;    % [m/s^2] Gravity.
mu  = 0.05;    % []     Rolling resistance coefficient.
eta = 0.85;    % []     Gearbox efficiency.

I_base       = 1.2;   % [A] Baseline motor current on flat ground.
K_slope_gain = 2.0;   % [A per unit sin(theta)] Slope current scaling gain.
K_accel_gain = 0.3;   % [A per (m/s^2)] Acceleration current scaling gain.
I_max        = 4.5;   % [A] Hardware current ceiling.

v_target = 0.6;        % [m/s] Desired cruise speed along the path.
dt       = 0.02;       % [s]   Simulation timestep (50 Hz, matching the CAN rate).
sim_time = 60;         % [s]   Total simulated duration.
n_steps  = round(sim_time / dt);

% Stanley controller gain: converts cross-track error into a steering-like
% yaw-rate correction. Higher k = more aggressive path correction.
k_stanley = 1.0;

%% ---------------------------------------------------------------------
% SECTION 3: REFERENCE PATH
% Simple straight-line path along the terrain's x-axis (y_ref = 0). The
% Stanley controller drives yaw-rate corrections to keep the robot on
% this line as it climbs/descends the terrain.
% ------------------------------------------------------------------------
path_x = x_terrain;
path_y = zeros(size(path_x));   % Straight path: desired y is always 0.
path_heading = zeros(size(path_x));  % Desired heading is 0 rad (pure +x travel).

%% ---------------------------------------------------------------------
% SECTION 4: MAIN SIMULATION LOOP
% State vector: [x, y, yaw, vx]. At each timestep we:
%   a) Find the current terrain slope at the robot's x position.
%   b) Run the Stanley controller to get a yaw-rate correction.
%   c) Compute 4-wheel kinematics (angular velocity per wheel).
%   d) Compute longitudinal load transfer (front vs rear normal force).
%   e) Compute required torque + slope-adaptive current per wheel.
%   f) Integrate the state forward by dt.
% ------------------------------------------------------------------------

% Preallocate all logging arrays for speed (avoids growing arrays in the loop).
log_x       = zeros(1, n_steps);
log_y       = zeros(1, n_steps);
log_yaw     = zeros(1, n_steps);
log_theta   = zeros(1, n_steps);   % Pitch angle (deg) at each step.
log_rpm     = zeros(4, n_steps);   % [FL; FR; RL; RR] wheel RPM.
log_torque  = zeros(1, n_steps);   % Per-motor torque (Nm).
log_current = zeros(4, n_steps);   % Per-motor current (A).
log_slip    = zeros(1, n_steps);   % Approximate slip ratio.
log_time    = (0:n_steps-1) * dt;

% Initial state.
state.x = 0; state.y = 0; state.yaw = 0; state.vx = 0;
prev_vx = 0;

for k = 1:n_steps
    % --- a) Look up terrain slope at the robot's current x position ---
    theta_rad = interp1(x_terrain, slope_terrain_rad, state.x, 'linear', 'extrap');
    theta_deg = rad2deg(theta_rad);

    % --- b) Stanley controller: cross-track + heading error correction ---
    [~, nearest_idx] = min(abs(path_x - state.x));   % Nearest path point.
    cross_track_error = state.y - path_y(nearest_idx);
    heading_error = path_heading(nearest_idx) - state.yaw;
    % Stanley law: yaw-rate command proportional to heading error plus an
    % arctan correction term for cross-track error (saturated by speed+1 to
    % avoid a singularity at very low speed).
    wz_cmd = heading_error + atan2(k_stanley * cross_track_error, state.vx + 0.5);

    % --- c) Longitudinal velocity control: simple proportional speed control ---
    vx_cmd = v_target;
    a_x = (vx_cmd - prev_vx) / dt;   % Numerically estimated longitudinal acceleration.
    prev_vx = vx_cmd;

    % --- 4-wheel kinematics: convert (vx_cmd, wz_cmd) to wheel omega [rad/s] ---
    half_track = (W + L) / 2;
    omega_fl = (vx_cmd - wz_cmd * half_track) / r;
    omega_fr = (vx_cmd + wz_cmd * half_track) / r;
    omega_rl = (vx_cmd - wz_cmd * half_track) / r;
    omega_rr = (vx_cmd + wz_cmd * half_track) / r;
    rpm = [omega_fl; omega_fr; omega_rl; omega_rr] * 60 / (2*pi);

    % --- d) Longitudinal load transfer during climbing ---
    % When pitched nose-up by theta, weight shifts toward the rear axle.
    % Standard static load-transfer equations for a 2-axle vehicle:
    Fz_total = M * g * cos(theta_rad);              % Total normal force (reduced by cos(theta) on a slope).
    Fz_rear  = Fz_total * (L/2 + M*g*sin(theta_rad)*0.15) / L;  % Rear axle share (rises with slope+height term).
    Fz_front = Fz_total - Fz_rear;                   % Front axle share is whatever remains.

    % --- e) Torque + current allocation (slope-adaptive) ---
    F_slope   = M * g * sin(theta_rad);              % Gravity component along the slope.
    F_rolling = M * g * mu * cos(theta_rad);         % Rolling resistance.
    F_inertial= M * a_x;                             % Force needed to accelerate.
    F_total   = F_slope + F_rolling + F_inertial;

    torque_per_motor = (F_total * r) / (4 * eta);    % Split across 4 driven wheels.
    current_slope_term = I_base + K_slope_gain*sin(theta_rad) + K_accel_gain*a_x;
    current_torque_term = torque_per_motor / Kt;
    current_cmd = min(max(current_slope_term, current_torque_term), I_max);  % Take the higher demand, clamp to max.

    % --- Approximate wheel slip ratio: (wheel surface speed - vehicle speed) / vehicle speed ---
    wheel_surface_speed = mean([omega_fl, omega_fr, omega_rl, omega_rr]) * r;
    slip_ratio = (wheel_surface_speed - state.vx) / max(state.vx, 0.05);

    % --- f) Integrate state forward (simple kinematic bicycle-style update) ---
    state.x   = state.x + state.vx * cos(state.yaw) * dt;
    state.y   = state.y + state.vx * sin(state.yaw) * dt;
    state.yaw = state.yaw + wz_cmd * dt;
    state.vx  = vx_cmd;  % Assume the low-level current control achieves the commanded speed.

    % --- Log everything for plotting ---
    log_x(k) = state.x; log_y(k) = state.y; log_yaw(k) = state.yaw;
    log_theta(k) = theta_deg;
    log_rpm(:,k) = rpm;
    log_torque(k) = torque_per_motor;
    log_current(:,k) = current_cmd;  % Same current command applied to all 4 motors here.
    log_slip(k) = slip_ratio;
end

%% ---------------------------------------------------------------------
% SECTION 5: FOUR-PANEL VISUALIZATION
% ------------------------------------------------------------------------
figure('Name', 'AMR Terrain Traversal Simulation', 'Position', [100 100 1200 800]);

% --- Panel 1: 3D trajectory over the terrain mesh ---
subplot(2,2,1);
[Xg, Yg] = meshgrid(x_terrain, linspace(-2, 2, 20));
Zg = repmat(z_terrain, 20, 1);   % Extrude the 1D terrain profile into a 2D mesh for visualization.
surf(Xg, Yg, Zg, 'EdgeColor', 'none', 'FaceAlpha', 0.6); hold on;
plot3(log_x, log_y, interp1(x_terrain, z_terrain, log_x, 'linear', 'extrap'), ...
      'r-', 'LineWidth', 2);
xlabel('X [m]'); ylabel('Y [m]'); zlabel('Z [m]');
title('3D Robot Trajectory over Terrain');
colormap(gca, 'summer'); view(35, 25);

% --- Panel 2: Motor RPM profile for all 4 wheels ---
subplot(2,2,2);
plot(log_time, log_rpm(1,:), 'LineWidth', 1.2); hold on;
plot(log_time, log_rpm(2,:), 'LineWidth', 1.2);
plot(log_time, log_rpm(3,:), '--', 'LineWidth', 1.2);
plot(log_time, log_rpm(4,:), '--', 'LineWidth', 1.2);
xlabel('Time [s]'); ylabel('RPM');
legend('FL', 'FR', 'RL', 'RR', 'Location', 'best');
title('Wheel RPM Profile'); grid on;

% --- Panel 3: Motor torque and scaled current draw ---
subplot(2,2,3);
yyaxis left;
plot(log_time, log_torque, 'b-', 'LineWidth', 1.5);
ylabel('Torque per Motor [Nm]');
yyaxis right;
plot(log_time, log_current(1,:), 'r-', 'LineWidth', 1.5);
ylabel('Current Command [A]');
xlabel('Time [s]');
title('Required Torque and Scaled Current Draw'); grid on;

% --- Panel 4: Pitch angle vs wheel slip ratio ---
subplot(2,2,4);
yyaxis left;
plot(log_time, log_theta, 'm-', 'LineWidth', 1.5);
ylabel('Pitch Angle \theta [deg]');
yyaxis right;
plot(log_time, log_slip, 'k-', 'LineWidth', 1.2);
ylabel('Slip Ratio [-]');
xlabel('Time [s]');
title('Robot Pitch vs Wheel Slip Ratio'); grid on;

sgtitle('4-Wheel Independent Drive AMR: Slope-Adaptive Traversal Simulation');
