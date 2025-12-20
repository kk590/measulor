from flask import Flask, render_template_string, request, jsonify
import cv2
import mediapipe as mp
import numpy as np
import json
import os
from datetime import datetime

app = Flask(__name__)

class AITailorSystem:
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            smooth_landmarks=True,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )
        self.mp_drawing = mp.solutions.drawing_utils
        self.pixel_to_cm_ratio = 0
        self.calibrated = False
        self.measurements_data = {}
        
    def calibrate_system(self, frame):
        h, w, _ = frame.shape
        face_width_pixels = w / 8
        average_face_width_cm = 15.5
        self.pixel_to_cm_ratio = average_face_width_cm / face_width_pixels
        self.calibrated = True
        return True
    
    def calculate_distance(self, point1, point2):
        return np.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)
    
    def extract_measurements(self, landmarks, frame_shape):
        h, w, _ = frame_shape
        
        landmarks_dict = {
            'left_shoulder': 11, 'right_shoulder': 12,
            'left_elbow': 13, 'right_elbow': 14,
            'left_wrist': 15, 'right_wrist': 16,
            'left_hip': 23, 'right_hip': 24,
            'left_ankle': 27, 'right_ankle': 28,
        }
        
        measurements = {}
        
        if self.pixel_to_cm_ratio == 0:
            return None
        
        try:
            left_shoulder = [landmarks[landmarks_dict['left_shoulder']].x * w, 
                           landmarks[landmarks_dict['left_shoulder']].y * h]
            right_shoulder = [landmarks[landmarks_dict['right_shoulder']].x * w, 
                            landmarks[landmarks_dict['right_shoulder']].y * h]
            shoulder_width = self.calculate_distance(left_shoulder, right_shoulder)
            measurements['Shoulder Width'] = round(shoulder_width * self.pixel_to_cm_ratio, 1)
            
            left_shoulder_pos = [landmarks[landmarks_dict['left_shoulder']].x * w,
                               landmarks[landmarks_dict['left_shoulder']].y * h]
            left_wrist_pos = [landmarks[landmarks_dict['left_wrist']].x * w,
                            landmarks[landmarks_dict['left_wrist']].y * h]
            arm_length = self.calculate_distance(left_shoulder_pos, left_wrist_pos)
            measurements['Left Arm Length'] = round(arm_length * self.pixel_to_cm_ratio, 1)
            
            left_hip = [landmarks[landmarks_dict['left_hip']].x * w,
                       landmarks[landmarks_dict['left_hip']].y * h]
            torso_length = self.calculate_distance(left_shoulder_pos, left_hip)
            measurements['Torso Length'] = round(torso_length * self.pixel_to_cm_ratio, 1)
            
            left_ankle = [landmarks[landmarks_dict['left_ankle']].x * w,
                         landmarks[landmarks_dict['left_ankle']].y * h]
            inseam = self.calculate_distance(left_hip, left_ankle)
            measurements['Inseam'] = round(inseam * self.pixel_to_cm_ratio, 1)
            
            right_hip = [landmarks[landmarks_dict['right_hip']].x * w,
                        landmarks[landmarks_dict['right_hip']].y * h]
            hip_width = self.calculate_distance(left_hip, right_hip)
            measurements['Hip Width'] = round(hip_width * self.pixel_to_cm_ratio, 1)
            
            leg_length = self.calculate_distance(left_hip, left_ankle)
            measurements['Leg Length'] = round(leg_length * self.pixel_to_cm_ratio, 1)
            
            return measurements
        except:
            return None
    
    def process_frame(self, frame):
        if not self.calibrated:
            self.calibrate_system(frame)
        
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(rgb_frame)
        
        if results.pose_landmarks:
            measurements = self.extract_measurements(results.pose_landmarks, frame.shape)
            return True, measurements
        
        return False, None
    
    def save_measurements(self, user_name, measurements):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if user_name not in self.measurements_data:
            self.measurements_data[user_name] = []
        
        self.measurements_data[user_name].append({
            'timestamp': timestamp,
            'measurements': measurements
        })
        return True

tailor_system = AITailorSystem()

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>AI Tailor - Body Measurement</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 800px;
            width: 100%;
            padding: 30px;
        }
        h1 {
            text-align: center;
            color: #333;
            margin-bottom: 10px;
            font-size: 2em;
        }
        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 15px;
            font-size: 0.9em;
        }
        .monetize-banner {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 12px;
            border-radius: 8px;
            text-align: center;
            margin-bottom: 20px;
            font-size: 0.85em;
            font-weight: 600;
        }
        .video-container {
            background: #000;
            border-radius: 15px;
            overflow: hidden;
            margin-bottom: 25px;
            aspect-ratio: 4/3;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        video { width: 100%; height: 100%; object-fit: cover; }
        .controls {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-bottom: 25px;
        }
        button {
            padding: 15px;
            border: none;
            border-radius: 10px;
            font-size: 1em;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .btn-primary {
            background: #667eea;
            color: white;
            grid-column: 1 / -1;
        }
        .btn-primary:hover {
            background: #5568d3;
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }
        .btn-secondary {
            background: #48bb78;
            color: white;
        }
        .btn-secondary:hover {
            background: #38a169;
            transform: translateY(-2px);
        }
        .btn-danger {
            background: #f56565;
            color: white;
        }
        .btn-danger:hover {
            background: #e53e3e;
        }
        .status-box {
            background: #f7fafc;
            border-left: 5px solid #667eea;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .status-item {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
        }
        .measurements-box {
            background: #f0f4ff;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .measurement-item {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #e2e8f0;
        }
        .alert {
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-weight: 500;
        }
        .alert-success { background: #c6f6d5; color: #22543d; }
        .alert-error { background: #fed7d7; color: #742a2a; }
        input {
            width: 100%;
            padding: 12px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            margin-bottom: 15px;
            font-size: 1em;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>👕 AI Tailor</h1>
        <p class="subtitle">Automatic Body Measurement System</p>
        
        <div class="monetize-banner">
            💝 Support on <a href="https://patreon.com" target="_blank" style="color:white; text-decoration:underline;">Patreon</a>
        </div>
        
        <div id="alert"></div>
        
        <div class="video-container">
            <video id="video" playsinline autoplay></video>
        </div>
        
        <div class="status-box">
            <div class="status-item">
                <span>Calibration:</span>
                <span id="calibration-status">Not Started</span>
            </div>
            <div class="status-item">
                <span>Detection:</span>
                <span id="detection-status">Waiting...</span>
            </div>
        </div>
        
        <div class="controls">
            <button class="btn-primary" onclick="calibrate()">📏 Calibrate</button>
            <button class="btn-secondary" onclick="measureNow()">📊 Measure</button>
            <button class="btn-danger" onclick="stopCamera()">⏹️ Stop</button>
        </div>
        
        <input type="text" id="username" placeholder="Enter your name" value="Guest">
        <button class="btn-primary" onclick="saveMeasurements()" style="width: 100%;">💾 Save</button>
        
        <div class="measurements-box" id="measurements-box" style="display: none;">
            <h3>📐 Measurements (cm)</h3>
            <div id="measurements-list"></div>
        </div>
    </div>
    
    <script>
        const video = document.getElementById('video');
        let calibrated = false;
        let currentMeasurements = null;
        
        navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } })
            .then(stream => {
                video.srcObject = stream;
                showAlert('Camera started!', 'success');
            })
            .catch(err => showAlert('Camera error: ' + err.message, 'error'));
        
        function calibrate() {
            fetch('/api/calibrate')
                .then(r => r.json())
                .then(d => {
                    calibrated = true;
                    document.getElementById('calibration-status').textContent = '✅ Calibrated';
                    showAlert('Calibrated!', 'success');
                });
        }
        
        function measureNow() {
            if (!calibrated) {
                showAlert('Calibrate first!', 'error');
                return;
            }
            fetch('/api/measure')
                .then(r => r.json())
                .then(d => {
                    if (d.success) {
                        currentMeasurements = d.measurements;
                        displayMeasurements(d.measurements);
                        showAlert('Measured!', 'success');
                    } else {
                        showAlert('No body detected', 'error');
                    }
                });
        }
        
        function displayMeasurements(m) {
            const list = document.getElementById('measurements-list');
            list.innerHTML = Object.entries(m).map(([k,v]) => 
                `<div class="measurement-item"><span>${k}</span><span>${v} cm</span></div>`
            ).join('');
            document.getElementById('measurements-box').style.display = 'block';
        }
        
        function saveMeasurements() {
            if (!currentMeasurements) {
                showAlert('No measurements!', 'error');
                return;
            }
            fetch('/api/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user: document.getElementById('username').value, measurements: currentMeasurements })
            }).then(r => r.json()).then(d => showAlert('Saved!', 'success'));
        }
        
        function stopCamera() {
            video.srcObject.getTracks().forEach(t => t.stop());
            showAlert('Camera stopped', 'success');
        }
        
        function showAlert(msg, type) {
            const box = document.getElementById('alert');
            box.className = `alert alert-${type}`;
            box.textContent = msg;
            setTimeout(() => box.textContent = '', 4000);
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/calibrate')
def calibrate():
    try:
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        cap.release()
        if ret:
            tailor_system.calibrate_system(frame)
            return jsonify({'success': True})
    except:
        pass
    return jsonify({'success': False})

@app.route('/api/measure')
def measure():
    try:
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        cap.release()
        if ret:
            success, measurements = tailor_system.process_frame(frame)
            if success and measurements:
                return jsonify({'success': True, 'measurements': measurements})
    except:
        pass
    return jsonify({'success': False})

@app.route('/api/save', methods=['POST'])
def save():
    try:
        data = request.json
        tailor_system.save_measurements(data['user'], data['measurements'])
        return jsonify({'success': True})
    except:
        return jsonify({'success': False})

# Vercel serverless function handler
from flask import Flask
from werkzeug.serving import WSGIRequestHandler

def handler(request):
    return app(request)
