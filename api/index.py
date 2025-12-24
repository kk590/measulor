from flask import Flask, jsonify, request
import base64
import io
import cv2
import numpy as np
import mediapipe as mp
from PIL import Image

app = Flask(__name__)

# Initialize MediaPipe Pose
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(static_image_mode=True, min_detection_confidence=0.5)

def calculate_distance(point1, point2):
    return np.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)

def get_body_measurements(image_array):
    results = pose.process(cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB))
    
    if not results.pose_landmarks:
        return None
    
    landmarks = results.pose_landmarks.landmark
    h, w = image_array.shape[:2]
    
    def get_coords(idx):
        return [landmarks[idx].x * w, landmarks[idx].y * h]
    
    measurements = {}
    
    # Shoulder width
    left_shoulder = get_coords(11)
    right_shoulder = get_coords(12)
    shoulder_width_px = calculate_distance(left_shoulder, right_shoulder)
    pixel_to_cm = 45.0 / shoulder_width_px if shoulder_width_px > 0 else 0.1
    measurements['shoulder_width'] = round(shoulder_width_px * pixel_to_cm, 1)
    
    # Hip width
    left_hip = get_coords(23)
    right_hip = get_coords(24)
    hip_width_px = calculate_distance(left_hip, right_hip)
    measurements['hip_width'] = round(hip_width_px * pixel_to_cm, 1)
    
    # Torso length
    torso_px = calculate_distance(left_shoulder, left_hip)
    measurements['torso_length'] = round(torso_px * pixel_to_cm, 1)
    
    # Arm length
    left_wrist = get_coords(15)
    arm_px = calculate_distance(left_shoulder, left_wrist)
    measurements['arm_length'] = round(arm_px * pixel_to_cm, 1)
    
    # Leg length
    left_ankle = get_coords(27)
    leg_px = calculate_distance(left_hip, left_ankle)
    measurements['leg_length'] = round(leg_px * pixel_to_cm, 1)
    
    # Body shape
    ratio = measurements['shoulder_width'] / measurements['hip_width'] if measurements['hip_width'] > 0 else 1
    if ratio > 1.05:
        body_shape = "Inverted Triangle"
    elif ratio < 0.95:
        body_shape = "Pear"
    else:
        body_shape = "Rectangle"
    
    measurements['body_shape'] = body_shape
    measurements['total_height'] = round((torso_px + leg_px) * pixel_to_cm, 1)
    
    return measurements

@app.route('/')
def index():
    return '''<!DOCTYPE html>
<html>
<head>
    <title>Measulor - AI Body Measurement</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; min-height: 100vh; color: white; padding: 15px; }
        .header { text-align: center; padding: 15px 0; }
        .header h1 { font-size: 1.8em; margin-bottom: 5px; }
        .camera-box { background: rgba(255,255,255,0.1); border-radius: 15px; padding: 15px; margin: 15px 0; }
        #video { width: 100%; border-radius: 10px; background: #000; }
        #canvas { display: none; }
        .controls { display: flex; gap: 10px; margin-top: 15px; }
        button { flex: 1; padding: 15px; border: none; border-radius: 10px; font-size: 1em; font-weight: 600; cursor: pointer; text-transform: uppercase; }
        .btn-primary { background: #48bb78; color: white; }
        .btn-secondary { background: #4299e1; color: white; }
        .status { background: rgba(255,255,255,0.1); border-radius: 10px; padding: 15px; text-align: center; margin: 15px 0; }
        .results { background: rgba(255,255,255,0.15); border-radius: 10px; padding: 20px; margin: 15px 0; display: none; }
        .measure-item { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.2); }
        .measure-label { font-weight: 600; }
        .measure-value { font-size: 1.1em; color: #48bb78; }
        .hidden { display: none; }
        .loading { display: inline-block; width: 20px; height: 20px; border: 3px solid rgba(255,255,255,.3); border-radius: 50%; border-top-color: #fff; animation: spin 1s ease-in-out infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="header">
        <h1>👕 Measulor</h1>
        <p>AI Body Measurement Tool</p>
    </div>
    <div class="camera-box">
        <video id="video" autoplay playsinline></video>
        <canvas id="canvas"></canvas>
        <div class="controls">
            <button class="btn-primary" id="startBtn" onclick="startCamera()">Start Camera</button>
            <button class="btn-secondary hidden" id="captureBtn" onclick="capturePhoto()">Measure Now</button>
        </div>
    </div>
    <div class="status" id="status">Tap "Start Camera" to begin</div>
    <div class="results" id="results"></div>
    <script>
        const video = document.getElementById('video');
        const canvas = document.getElementById('canvas');
        const startBtn = document.getElementById('startBtn');
        const captureBtn = document.getElementById('captureBtn');
        const status = document.getElementById('status');
        const results = document.getElementById('results');
        async function startCamera() {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } } });
                video.srcObject = stream;
                startBtn.classList.add('hidden');
                captureBtn.classList.remove('hidden');
                status.innerHTML = '✅ Camera active! Stand in T-pose and tap Measure';
            } catch (err) { status.innerHTML = '❌ Camera access denied'; }
        }
        function capturePhoto() {
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            canvas.getContext('2d').drawImage(video, 0, 0);
            status.innerHTML = '<div class="loading"></div> Processing... (5-10 seconds)';
            results.style.display = 'none';
            fetch('/api/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image: canvas.toDataURL('image/jpeg', 0.8) })
            })
            .then(r => r.json())
            .then(data => {
                if (data.success && data.measurements) {
                    displayResults(data.measurements);
                    status.innerHTML = '✅ Measurements complete!';
                } else {
                    status.innerHTML = '❌ ' + (data.message || 'No body detected. Try T-pose!');
                }
            })
            .catch(() => { status.innerHTML = '❌ Error processing image'; });
        }
        function displayResults(m) {
            results.innerHTML = `
                <h3 style="margin-bottom: 15px; text-align: center;">📊 Your Measurements</h3>
                <div class="measure-item"><span class="measure-label">Shoulder Width:</span><span class="measure-value">${m.shoulder_width} cm</span></div>
                <div class="measure-item"><span class="measure-label">Hip Width:</span><span class="measure-value">${m.hip_width} cm</span></div>
                <div class="measure-item"><span class="measure-label">Torso Length:</span><span class="measure-value">${m.torso_length} cm</span></div>
                <div class="measure-item"><span class="measure-label">Arm Length:</span><span class="measure-value">${m.arm_length} cm</span></div>
                <div class="measure-item"><span class="measure-label">Leg Length:</span><span class="measure-value">${m.leg_length} cm</span></div>
                <div class="measure-item"><span class="measure-label">Est. Height:</span><span class="measure-value">${m.total_height} cm</span></div>
                <div class="measure-item" style="border:none;"><span class="measure-label">Body Shape:</span><span class="measure-value">${m.body_shape}</span></div>
            `;
            results.style.display = 'block';
        }
    </script>
</body>
</html>'''

@app.route('/api/process', methods=['POST'])
def process_image():
    try:
        data = request.json
        image_data = data.get('image', '')
        if not image_data:
            return jsonify({'success': False, 'message': 'No image provided'})
        if 'base64,' in image_data:
            image_data = image_data.split('base64,')[1]
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))
        image_array = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        measurements = get_body_measurements(image_array)
        if measurements:
            return jsonify({'success': True, 'message': 'Measurements calculated', 'measurements': measurements})
        else:
            return jsonify({'success': False, 'message': 'No body detected. Stand in T-pose with full body visible.'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'message': 'MediaPipe body measurement API ready!'})

if __name__ == '__main__':
    app.run()
