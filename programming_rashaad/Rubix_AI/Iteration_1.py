import os
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import PIL.Image
import json
import requests
import sqlite3
from datetime import datetime
import PyPDF2

# --- Configuration ---
YOUR_API_KEY = "AIzaSyBSDI7Hpsha7PfcgQgBD6YWfGWCNpG_KFM"
YOUR_WEATHER_API_KEY = "YOUR_OPENWEATHER_API_KEY_HERE"

try:
    genai.configure(api_key=YOUR_API_KEY)
except Exception as e:
    print(f"ERROR: Could not configure genai: {e}")
    exit()

# Setup Flask
app = Flask(__name__)
CORS(app)

# Configure Upload Folder
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Configure Generative Models
text_model = genai.GenerativeModel('gemini-pro')
vision_model = genai.GenerativeModel('gemini-pro-vision')

# --- Database Setup ---
def init_db():
    conn = sqlite3.connect('rubixai.db')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS chat_history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TEXT,
                  role TEXT,
                  message TEXT,
                  session_id TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS images
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TEXT,
                  filename TEXT,
                  file_data BLOB,
                  file_type TEXT,
                  description TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS documents
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TEXT,
                  filename TEXT,
                  content TEXT,
                  file_type TEXT)''')

    conn.commit()
    conn.close()

init_db()

SYSTEM_PROMPT = """
You are RubixAI, an advanced AI assistant with multimodal capabilities.
You can analyze images, process documents, perform complex calculations, and solve coding problems.
You are helpful, precise, and efficient. When analyzing content, provide detailed insights.
"""

# ==========================================================================
# --- FRONTEND: HTML / CSS / JS all embedded in one template string ---
# ==========================================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RUBIXAI - Advanced AI Assistant</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body, html {
            overflow: hidden;
            background-color: #FFFFFF;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Google Sans", sans-serif;
            color: #333;
            height: 100%;
            width: 100%;
        }

        canvas {
            display: block;
            width: 100%;
            height: 100%;
            position: fixed;
            top: 0;
            left: 0;
            z-index: 1;
        }

        /* --- Chat Container (Right Side, Always Open) --- */
        #chat-container {
            position: fixed;
            right: 0;
            top: 0;
            bottom: 0;
            width: 400px;
            background: rgba(255, 255, 255, 0.98);
            backdrop-filter: blur(10px);
            box-shadow: -4px 0 24px rgba(0,0,0,0.1);
            z-index: 100;
            display: flex;
            flex-direction: column;
            border-left: 1px solid #e0e0e0;
        }

        #chat-header {
            padding: 20px;
            background: linear-gradient(135deg, #4285F4 0%, #34A853 100%);
            color: white;
            border-bottom: 1px solid rgba(255,255,255,0.2);
        }

        #chat-title {
            font-size: 1.3rem;
            font-weight: 600;
            margin-bottom: 4px;
        }

        #chat-subtitle {
            font-size: 0.85rem;
            opacity: 0.9;
        }

        #chat-history {
            flex-grow: 1;
            overflow-y: auto;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 14px;
        }

        #chat-history::-webkit-scrollbar { width: 6px; }
        #chat-history::-webkit-scrollbar-track { background: #f1f1f1; }
        #chat-history::-webkit-scrollbar-thumb { background: #c1c1c1; border-radius: 3px; }
        #chat-history::-webkit-scrollbar-thumb:hover { background: #a1a1a1; }

        .message {
            max-width: 85%;
            padding: 12px 16px;
            border-radius: 18px;
            word-wrap: break-word;
            line-height: 1.5;
            animation: messageSlideIn 0.3s ease-out;
        }

        @keyframes messageSlideIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .user-message {
            align-self: flex-end;
            background: linear-gradient(135deg, #4285F4 0%, #34A853 100%);
            color: white;
            border-bottom-right-radius: 4px;
        }

        .ai-message {
            align-self: flex-start;
            background-color: #f1f3f4;
            color: #202124;
            border-bottom-left-radius: 4px;
        }

        .ai-message mark {
            background-color: #FBBC05;
            color: #3c4043;
            border-radius: 3px;
            padding: 2px 5px;
            font-weight: 500;
        }

        #file-preview-container {
            padding: 12px 16px;
            border-bottom: 1px solid #e0e0e0;
            background: #f8f9fa;
            position: relative;
        }

        #file-preview {
            max-width: 100%;
            height: auto;
            max-height: 120px;
            border-radius: 8px;
            display: none;
            margin-bottom: 8px;
        }

        #file-name {
            font-size: 0.9rem;
            color: #5f6368;
            word-break: break-all;
        }

        #remove-file-btn {
            position: absolute;
            top: 16px;
            right: 20px;
            background: rgba(0,0,0,0.6);
            color: white;
            border: none;
            border-radius: 50%;
            width: 26px;
            height: 26px;
            font-size: 18px;
            line-height: 26px;
            cursor: pointer;
            transition: background 0.2s;
        }

        #remove-file-btn:hover { background: rgba(0,0,0,0.8); }

        #file-type-selector {
            padding: 6px 10px;
            border: 1px solid #dadce0;
            border-radius: 6px;
            background: white;
            font-size: 0.85rem;
            color: #5f6368;
            cursor: pointer;
            margin-right: 8px;
            outline: none;
        }

        #file-type-selector:focus { border-color: #4285F4; }

        #chat-input-container {
            border-top: 1px solid #e0e0e0;
            padding: 16px;
            display: flex;
            align-items: center;
            background: #ffffff;
            gap: 8px;
        }

        #chat-input {
            flex-grow: 1;
            border: 1px solid #dadce0;
            outline: none;
            background: #f8f9fa;
            font-size: 0.95rem;
            padding: 10px 14px;
            color: #333;
            border-radius: 24px;
            transition: all 0.2s;
            resize: none;
            font-family: inherit;
        }

        #chat-input:focus {
            background: white;
            border-color: #4285F4;
            box-shadow: 0 0 0 3px rgba(66, 133, 244, 0.1);
        }

        #chat-input::placeholder { color: #999; }

        #chat-send-btn {
            background: linear-gradient(135deg, #4285F4 0%, #34A853 100%);
            border: none;
            border-radius: 50%;
            width: 44px;
            height: 44px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: transform 0.2s, box-shadow 0.2s;
            flex-shrink: 0;
        }

        #chat-send-btn:hover {
            transform: scale(1.05);
            box-shadow: 0 4px 12px rgba(66, 133, 244, 0.3);
        }

        #chat-send-btn svg {
            fill: white;
            width: 20px;
            height: 20px;
            transform: translateX(1px);
        }

        #upload-btn {
            background-color: #f1f3f4;
            border: none;
            border-radius: 50%;
            width: 44px;
            height: 44px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            transition: background 0.2s;
        }

        #upload-btn:hover { background-color: #e8eaed; }

        #upload-btn svg {
            fill: #5f6368;
            width: 24px;
            height: 24px;
        }

        #content-container {
            position: fixed;
            left: 0;
            top: 0;
            right: 400px;
            bottom: 0;
            padding: 30px;
            z-index: 10;
            display: flex;
            flex-direction: column;
        }

        #header-section {
            display: flex;
            align-items: flex-start;
            gap: 30px;
        }

        #logo-section { flex-shrink: 0; }

        #title {
            font-size: 3rem;
            font-weight: 700;
            background: linear-gradient(135deg, #4285F4 0%, #EA4335 50%, #34A853 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            letter-spacing: -1px;
            margin-bottom: 10px;
        }

        #subtitle {
            font-size: 1rem;
            color: #5f6368;
            font-weight: 400;
        }

        #weather-widget {
            background: linear-gradient(135deg, rgba(66, 133, 244, 0.1) 0%, rgba(52, 168, 83, 0.1) 100%);
            border: 1px solid rgba(66, 133, 244, 0.2);
            border-radius: 16px;
            padding: 16px 20px;
            display: flex;
            align-items: center;
            gap: 12px;
            min-width: 250px;
            backdrop-filter: blur(10px);
        }

        #weather-icon img { width: 48px; height: 48px; }

        #weather-info {
            display: flex;
            flex-direction: column;
            gap: 2px;
        }

        #weather-temp {
            font-size: 1.5rem;
            font-weight: 600;
            color: #3c4043;
        }

        #weather-desc {
            font-size: 0.9rem;
            color: #5f6368;
        }

        #info {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 1.3rem;
            color: #5f6368;
            z-index: 10;
            text-align: center;
            padding: 0 20px;
        }

        #startButton {
            position: fixed;
            top: 55%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 1.3rem;
            padding: 16px 40px;
            border: none;
            border-radius: 30px;
            background: linear-gradient(135deg, #4285F4 0%, #34A853 100%);
            color: white;
            cursor: pointer;
            box-shadow: 0 8px 24px rgba(66, 133, 244, 0.3);
            transition: all 0.3s ease;
            z-index: 100;
            font-weight: 500;
            letter-spacing: 0.5px;
        }

        #startButton:hover {
            transform: translate(-50%, -50%) scale(1.05);
            box-shadow: 0 12px 32px rgba(66, 133, 244, 0.4);
        }

        .hidden { display: none !important; }

        @media (max-width: 1024px) {
            #chat-container { width: 350px; }
            #content-container { right: 350px; }
            #title { font-size: 2.5rem; }
        }

        @media (max-width: 768px) {
            #chat-container { width: 100%; max-width: 100%; }
            #content-container { display: none; }
            #info, #startButton { left: 50%; transform: translate(-50%, -50%); }
        }
    </style>
</head>
<body>
    <!-- Chat Container (Right Side, Always Open) -->
    <div id="chat-container">
        <div id="chat-header">
            <div id="chat-title">RubixAI Chat</div>
            <div id="chat-subtitle">Your intelligent assistant</div>
        </div>

        <div id="chat-history">
            <div class="message ai-message">
                Hello! I'm RubixAI, your advanced AI assistant. I can analyze images, process documents, perform complex calculations, and help with coding problems. How can I assist you today?
            </div>
        </div>

        <div id="file-preview-container" class="hidden">
            <img id="file-preview" src="#" alt="File preview" />
            <div id="file-name"></div>
            <button id="remove-file-btn" aria-label="Remove file">&times;</button>
        </div>

        <div id="chat-input-container">
            <input type="file" id="upload-input" accept="image/*,.pdf,.doc,.docx,.txt" class="hidden">

            <select id="file-type-selector">
                <option value="image">Image</option>
                <option value="document">Document</option>
            </select>

            <button id="upload-btn" aria-label="Upload file">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M9 16h6v-6h4l-7-7-7 7h4zm-4 2h14v2H5z"/>
                </svg>
            </button>

            <input type="text" id="chat-input" placeholder="Type your message...">

            <button id="chat-send-btn" aria-label="Send message">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
                    <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                </svg>
            </button>
        </div>
    </div>

    <!-- Main Content (Left Side) -->
    <div id="content-container">
        <div id="header-section">
            <div id="logo-section">
                <div id="title">RUBIXAI</div>
                <div id="subtitle">Advanced AI • Voice Enabled • Multi-Modal</div>
            </div>

            <div id="weather-widget">
                <span id="weather-icon"></span>
                <div id="weather-info">
                    <span id="weather-temp">--°C</span>
                    <span id="weather-desc">Loading weather...</span>
                </div>
            </div>
        </div>

        <div id="info">Click "Start" to enable audio</div>
        <button id="startButton">Start Audio System</button>
    </div>

    <!-- Canvas for Particle Animation -->
    <canvas id="orbCanvas"></canvas>

    <script type="importmap">
        {
            "imports": {
                "three": "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.module.js"
            }
        }
    </script>
    <script type="module">
        import * as THREE from 'three';

        // --- Global Variables ---
        let scene, camera, renderer, particles, analyser, dataArray;
        let audioContext;
        let currentInstability = 0;
        let targetInstability = 0;
        const particleCount = 1500;
        const sphereRadius = 2.5;
        let originalPositions = [];
        let jsChatHistory = [];
        let uploadedFile = null;
        let currentFileType = 'image';
        const synth = window.speechSynthesis;
        const sessionId = 'session_' + Date.now();

        // --- API URLs ---
        const CHAT_API_URL = '/api/chat';
        const WEATHER_API_URL = '/api/weather';
        const CHAT_HISTORY_URL = '/api/chat/history';

        // --- DOM Elements ---
        const canvas = document.getElementById('orbCanvas');
        const infoText = document.getElementById('info');
        const startButton = document.getElementById('startButton');

        // Chat Elements
        const chatHistoryEl = document.getElementById('chat-history');
        const chatInput = document.getElementById('chat-input');
        const sendButton = document.getElementById('chat-send-btn');
        const uploadBtn = document.getElementById('upload-btn');
        const uploadInput = document.getElementById('upload-input');
        const filePreviewContainer = document.getElementById('file-preview-container');
        const filePreview = document.getElementById('file-preview');
        const removeFileBtn = document.getElementById('remove-file-btn');
        const fileTypeSelector = document.getElementById('file-type-selector');

        // Weather Elements
        const weatherIconEl = document.getElementById('weather-icon');
        const weatherTempEl = document.getElementById('weather-temp');
        const weatherDescEl = document.getElementById('weather-desc');

        // --- Colors ---
        const colors = [
            new THREE.Color("#4285F4"), new THREE.Color("#EA4335"),
            new THREE.Color("#34A853"), new THREE.Color("#FBBC05")
        ];
        const stableColors = [colors[0], colors[1], colors[2]];
        const allColors = [colors[0], colors[1], colors[2], colors[3]];

        // --- Initialization ---
        function init() {
            scene = new THREE.Scene();
            camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
            camera.position.z = 5;

            renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true, alpha: true });
            renderer.setSize(window.innerWidth, window.innerHeight);
            renderer.setPixelRatio(window.devicePixelRatio);
            renderer.setClearColor(0xFFFFFF, 1);

            // Particle system
            const geometry = new THREE.BufferGeometry();
            const positions = [];
            const particleColors = [];
            for (let i = 0; i < particleCount; i++) {
                const u = Math.random();
                const v = Math.random();
                const theta = 2 * Math.PI * u;
                const phi = Math.acos(2 * v - 1);
                const x = sphereRadius * Math.sin(phi) * Math.cos(theta);
                const y = sphereRadius * Math.sin(phi) * Math.sin(theta);
                const z = sphereRadius * Math.cos(phi);
                positions.push(x, y, z);
                originalPositions.push(new THREE.Vector3(x, y, z));
                const color = stableColors[Math.floor(Math.random() * stableColors.length)];
                particleColors.push(color.r, color.g, color.b);
            }
            geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
            geometry.setAttribute('color', new THREE.Float32BufferAttribute(particleColors, 3));
            const material = new THREE.PointsMaterial({
                size: 0.05,
                vertexColors: true,
                sizeAttenuation: true
            });
            particles = new THREE.Points(geometry, material);
            scene.add(particles);

            // Event Listeners
            window.addEventListener('resize', onWindowResize);
            startButton.addEventListener('click', startAudio);

            sendButton.addEventListener('click', handleSendMessage);
            chatInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                }
            });

            uploadBtn.addEventListener('click', () => uploadInput.click());
            uploadInput.addEventListener('change', handleFileSelect);
            removeFileBtn.addEventListener('click', clearFilePreview);

            // Load chat history
            loadChatHistory();

            // Fetch weather
            fetchWeather();
        }

        function handleFileSelect(event) {
            const file = event.target.files[0];
            if (!file) return;

            uploadedFile = file;
            const fileType = fileTypeSelector.value;
            currentFileType = fileType;

            if (fileType === 'image' && file.type.startsWith('image/')) {
                filePreview.src = URL.createObjectURL(file);
                filePreview.style.display = 'block';
            } else {
                filePreview.style.display = 'none';
                filePreview.src = '#';
            }

            document.getElementById('file-name').textContent = file.name;
            filePreviewContainer.classList.remove('hidden');
        }

        function clearFilePreview() {
            uploadedFile = null;
            uploadInput.value = null;
            filePreviewContainer.classList.add('hidden');
            filePreview.src = '#';
            document.getElementById('file-name').textContent = '';
        }

        function startAudio() {
            startButton.style.display = 'none';
            infoText.textContent = "Listening...";

            audioContext = new (window.AudioContext || window.webkitAudioContext)();
            analyser = audioContext.createAnalyser();
            analyser.fftSize = 256;
            const bufferLength = analyser.frequencyBinCount;
            dataArray = new Uint8Array(bufferLength);

            navigator.mediaDevices.getUserMedia({ audio: true })
                .then(stream => {
                    const source = audioContext.createMediaStreamSource(stream);
                    source.connect(analyser);
                    speakJarvisStyle("Audio system initialized. I am now listening.");
                })
                .catch(err => {
                    console.error('Error getting audio', err);
                    infoText.textContent = "Error: Could not access microphone.";
                });
        }

        function animate() {
            requestAnimationFrame(animate);

            if (analyser) {
                analyser.getByteFrequencyData(dataArray);
                let averageVolume = 0;
                for (let i = 0; i < dataArray.length; i++) {
                    averageVolume += dataArray[i];
                }
                averageVolume /= dataArray.length;

                const noiseThreshold = 20;
                if (averageVolume > noiseThreshold) {
                    targetInstability = Math.min((averageVolume - noiseThreshold) / 50, 1.0) * 2.0;
                    infoText.textContent = "Processing audio input...";
                } else {
                    targetInstability = 0;
                    infoText.textContent = "Listening...";
                }

                currentInstability += (targetInstability - currentInstability) * 0.1;
                updateParticles(currentInstability);
            } else {
                currentInstability += (0 - currentInstability) * 0.1;
                updateParticles(currentInstability);
            }

            particles.rotation.y += 0.001 + currentInstability * 0.002;
            particles.rotation.x += 0.0005;
            renderer.render(scene, camera);
        }

        function updateParticles(instability) {
            const positions = particles.geometry.attributes.position.array;
            const colorsAttr = particles.geometry.attributes.color.array;

            for (let i = 0; i < particleCount; i++) {
                const i3 = i * 3;
                const originalPos = originalPositions[i];

                const noise = (Math.random() - 0.5) * instability * 2.0 + (Math.random() - 0.5) * 0.01;
                const expansion = 1.0 + instability * 0.5;

                const targetX = originalPos.x * expansion + noise;
                const targetY = originalPos.y * expansion + noise;
                const targetZ = originalPos.z * expansion + noise;

                positions[i3] = lerp(positions[i3], targetX, 0.1);
                positions[i3 + 1] = lerp(positions[i3 + 1], targetY, 0.1);
                positions[i3 + 2] = lerp(positions[i3 + 2], targetZ, 0.1);

                if (Math.random() < 0.005 + instability * 0.05) {
                    const colorSet = instability > 0.1 ? allColors : stableColors;
                    const newColor = colorSet[Math.floor(Math.random() * colorSet.length)];
                    colorsAttr[i3] = newColor.r;
                    colorsAttr[i3 + 1] = newColor.g;
                    colorsAttr[i3 + 2] = newColor.b;
                }
            }

            particles.geometry.attributes.position.needsUpdate = true;
            particles.geometry.attributes.color.needsUpdate = true;
        }

        function onWindowResize() {
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        }

        function lerp(start, end, amt) {
            return (1 - amt) * start + amt * end;
        }

        function speakJarvisStyle(text) {
            if (synth.speaking) {
                synth.cancel();
            }

            if (text !== '') {
                const utterance = new SpeechSynthesisUtterance(text);
                utterance.rate = 0.9;
                utterance.pitch = 0.8;
                utterance.volume = 1.0;

                const voices = synth.getVoices();
                const preferredVoice = voices.find(voice =>
                    voice.name.includes('Google UK English Male') ||
                    voice.name.includes('Male') ||
                    voice.lang.includes('en')
                );

                if (preferredVoice) {
                    utterance.voice = preferredVoice;
                }

                utterance.onerror = (event) => console.error('Speech error:', event);
                synth.speak(utterance);
            }
        }

        function addMessageToHistory(htmlContent, sender) {
            const messageElement = document.createElement('div');
            messageElement.classList.add('message', `${sender}-message`);
            messageElement.innerHTML = htmlContent;
            chatHistoryEl.appendChild(messageElement);
            chatHistoryEl.scrollTop = chatHistoryEl.scrollHeight;
            return messageElement;
        }

        async function handleSendMessage() {
            const messageText = chatInput.value.trim();
            if (messageText === '' && !uploadedFile) return;

            const safeUserMessage = document.createTextNode(messageText || 'Analyzing file...').textContent;
            addMessageToHistory(safeUserMessage, 'user');
            jsChatHistory.push({ role: "user", parts: [messageText] });

            const formData = new FormData();
            formData.append('message', messageText);
            formData.append('history', JSON.stringify(jsChatHistory));
            formData.append('session_id', sessionId);

            if (uploadedFile) {
                formData.append('file', uploadedFile);
                formData.append('file_type', currentFileType);
            }

            chatInput.value = '';
            clearFilePreview();

            const thinkingMessage = addMessageToHistory('Processing...', 'ai');

            try {
                const response = await fetch(CHAT_API_URL, {
                    method: 'POST',
                    body: formData,
                });

                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                const data = await response.json();

                thinkingMessage.innerHTML = data.reply;
                jsChatHistory.push({ role: "model", parts: [data.reply] });

                speakJarvisStyle(stripHTML(data.reply));

            } catch (error) {
                console.error('Error sending chat message:', error);
                thinkingMessage.innerHTML = 'Sorry, I encountered an error. Please try again.';
                speakJarvisStyle("An error occurred. Please try again.");
            }
        }

        function stripHTML(html) {
            const tmp = document.createElement('div');
            tmp.innerHTML = html;
            return tmp.textContent || tmp.innerText || '';
        }

        async function loadChatHistory() {
            try {
                const response = await fetch(`${CHAT_HISTORY_URL}?session_id=${sessionId}&limit=20`);
                if (!response.ok) return;

                const data = await response.json();
                if (data.history && data.history.length > 0) {
                    data.history.forEach(msg => {
                        addMessageToHistory(msg.message, msg.role === 'user' ? 'user' : 'ai');
                        jsChatHistory.push({ role: msg.role, parts: [msg.message] });
                    });
                }
            } catch (error) {
                console.error('Error loading chat history:', error);
            }
        }

        function fetchWeather() {
            if (!navigator.geolocation) {
                weatherDescEl.textContent = 'Geolocation not supported';
                return;
            }

            navigator.geolocation.getCurrentPosition(async (position) => {
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;

                try {
                    const response = await fetch(`${WEATHER_API_URL}?lat=${lat}&lon=${lon}`);
                    if (!response.ok) throw new Error('Failed to fetch weather');
                    const data = await response.json();

                    const temp = Math.round(data.main.temp);
                    const desc = data.weather[0].description;
                    const icon = data.weather[0].icon;

                    weatherIconEl.innerHTML = `<img src="https://openweathermap.org/img/wn/${icon}@2x.png" alt="Weather">`;
                    weatherTempEl.textContent = `${temp}°C`;
                    weatherDescEl.textContent = desc.charAt(0).toUpperCase() + desc.slice(1);

                } catch (error) {
                    console.error('Error fetching weather:', error);
                    weatherDescEl.textContent = 'Weather unavailable';
                }
            }, () => {
                weatherDescEl.textContent = 'Location access denied';
            });
        }

        // Start everything
        init();
        animate();
    </script>
</body>
</html>
"""

# ==========================================================================
# --- ROUTES ---
# ==========================================================================

@app.route('/')
def serve_index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/weather')
def get_weather():
    lat = request.args.get('lat')
    lon = request.args.get('lon')

    if not lat or not lon:
        return jsonify({"error": "Missing latitude or longitude"}), 400

    if YOUR_WEATHER_API_KEY == "YOUR_OPENWEATHER_API_KEY_HERE":
        return jsonify({
            "weather": [{"description": "sunny", "icon": "01d"}],
            "main": {"temp": 25}
        })

    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={YOUR_WEATHER_API_KEY}&units=metric"
        response = requests.get(url)
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": f"An error occurred: {e}"}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        user_message = request.form.get('message', '')
        history_json = request.form.get('history', '[]')
        session_id = request.form.get('session_id', 'default')
        file_data = request.files.get('file')
        file_type = request.form.get('file_type', 'image')

        chat_history = json.loads(history_json)

        if not user_message and not file_data:
            return jsonify({"error": "No message or file provided"}), 400

        save_chat_message(session_id, "user", user_message)

        response_text = ""

        if file_data:
            filename = file_data.filename

            if file_type == 'image':
                image_path = os.path.join(UPLOAD_FOLDER, filename)
                file_data.save(image_path)

                with open(image_path, 'rb') as f:
                    image_blob = f.read()
                save_image(filename, image_blob, file_data.content_type, user_message)

                img = PIL.Image.open(image_path)
                prompt_parts = [SYSTEM_PROMPT, user_message, img]
                response = vision_model.generate_content(prompt_parts)
                response_text = response.text.strip()

                os.remove(image_path)

            elif file_type == 'document':
                file_content = extract_document_content(file_data, filename)
                save_document(filename, file_content, file_data.content_type)

                full_prompt = f"{SYSTEM_PROMPT}\n\nDocument Content:\n{file_content}\n\nUser Query: {user_message}\n\nProvide a detailed analysis:"
                response = text_model.generate_content(full_prompt)
                response_text = response.text.strip()
        else:
            chat_session = text_model.start_chat(history=chat_history)
            full_prompt = f"{SYSTEM_PROMPT}\nUser: {user_message}"
            response = chat_session.send_message(full_prompt)
            response_text = response.text.strip()

        save_chat_message(session_id, "model", response_text)

        return jsonify({"reply": response_text})

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": f"An error occurred on the server: {e}"}), 500

@app.route('/api/chat/history', methods=['GET'])
def get_chat_history():
    session_id = request.args.get('session_id', 'default')
    limit = request.args.get('limit', 50)

    conn = sqlite3.connect('rubixai.db')
    c = conn.cursor()
    c.execute('''SELECT timestamp, role, message FROM chat_history
                 WHERE session_id = ? ORDER BY id DESC LIMIT ?''', (session_id, limit))
    rows = c.fetchall()
    conn.close()

    history = [{"timestamp": r[0], "role": r[1], "message": r[2]} for r in reversed(rows)]
    return jsonify({"history": history})

def extract_document_content(file_obj, filename):
    """Extract text content from various document types (no python-docx dependency)"""
    ext = filename.lower().split('.')[-1]

    try:
        if ext == 'pdf':
            pdf_reader = PyPDF2.PdfReader(file_obj)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text

        elif ext in ['docx', 'doc']:
            try:
                import zipfile
                import xml.etree.ElementTree as ET

                with zipfile.ZipFile(file_obj) as docx:
                    xml_content = docx.read('word/document.xml')
                    tree = ET.XML(xml_content)

                    paragraphs = []
                    for paragraph in tree.iter():
                        if paragraph.tag.endswith('t'):
                            if paragraph.text:
                                paragraphs.append(paragraph.text)

                    return '\n'.join(paragraphs)
            except Exception as e:
                return f"Error reading DOCX file: {str(e)}"

        elif ext == 'txt':
            return file_obj.read().decode('utf-8')

        else:
            return "Unsupported document format. Supported: PDF, TXT, DOCX"

    except Exception as e:
        return f"Error extracting document: {str(e)}"

def save_chat_message(session_id, role, message):
    conn = sqlite3.connect('rubixai.db')
    c = conn.cursor()
    timestamp = datetime.now().isoformat()
    c.execute('INSERT INTO chat_history (timestamp, role, message, session_id) VALUES (?, ?, ?, ?)',
              (timestamp, role, message, session_id))
    conn.commit()
    conn.close()

def save_image(filename, file_data, file_type, description):
    conn = sqlite3.connect('rubixai.db')
    c = conn.cursor()
    timestamp = datetime.now().isoformat()
    c.execute('INSERT INTO images (timestamp, filename, file_data, file_type, description) VALUES (?, ?, ?, ?, ?)',
              (timestamp, filename, file_data, file_type, description))
    conn.commit()
    conn.close()

def save_document(filename, content, file_type):
    conn = sqlite3.connect('rubixai.db')
    c = conn.cursor()
    timestamp = datetime.now().isoformat()
    c.execute('INSERT INTO documents (timestamp, filename, content, file_type) VALUES (?, ?, ?, ?)',
              (timestamp, filename, content, file_type))
    conn.commit()
    conn.close()

if __name__ == '__main__':
    print("="*50)
    print("Starting RubixAI (Single File Edition)")
    print("Your app is now running at: http://127.0.0.1:5000")
    print("="*50)
    app.run(port=5000, debug=True)