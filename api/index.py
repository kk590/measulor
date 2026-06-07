from flask import Flask, jsonify, request
import base64
import io
import os
import random
from PIL import Image

app = Flask(__name__)


def generate_demo_measurements(width, height):
    """Generate measurements"""
    measurements = {
        'shoulder_width': round(random.uniform(38.0, 50.0), 1),
        'hip_width': round(random.uniform(32.0, 42.0), 1),
        'torso_length': round(random.uniform(55.0, 70.0), 1),
        'arm_length': round(random.uniform(55.0, 65.0), 1),
        'leg_length': round(random.uniform(85.0, 105.0), 1)
    }
    measurements['total_height'] = round(measurements['torso_length'] + measurements['leg_length'], 1)
    ratio = measurements['shoulder_width'] / measurements['hip_width']
    if ratio > 1.05:
        body_shape = "Inverted Triangle"
    elif ratio < 0.95:
        body_shape = "Pear"
    else:
        body_shape = "Rectangle"
    measurements['body_shape'] = body_shape
    return measurements

@app.route('/')
def index():
    return '''<!DOCTYPE html>
<html>
<head>
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-4630566819144819" crossorigin="anonymous"></script>
    <title>Measulor - AI Body Measurement</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); font-family: -apple-system, sans-serif; min-height: 100vh; color: white; padding: 15px; }
        .header { text-align: center; padding: 15px 0; }
        .header h1 { font-size: 2.2em; margin-bottom: 10px; }
        .header p { font-size: 1.1em; opacity: 0.9; }
        .measurement-app { max-width: 600px; margin: 0 auto; }
        .camera-box { background: rgba(255,255,255,0.1); border-radius: 15px; padding: 15px; margin: 15px 0; }
        #video { width: 100%; border-radius: 10px; background: #000; }
        #canvas { display: none; }
        .controls { display: flex; gap: 10px; margin-top: 15px; }
        .btn-primary { background: #48bb78; color: white; border: none; padding: 15px; border-radius: 10px; font-size: 1em; cursor: pointer; }
        .btn-secondary { background: #4299e1; color: white; border: none; padding: 15px; border-radius: 10px; font-size: 1em; cursor: pointer; }
        .status { background: rgba(255,255,255,0.1); border-radius: 10px; padding: 15px; text-align: center; margin: 15px 0; }
        .results { background: rgba(255,255,255,0.15); border-radius: 10px; padding: 20px; margin: 15px 0; display: none; }
        .measure-item { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.2); }
        .instruction-box { background: rgba(255,255,255,0.15); padding: 15px; border-radius: 10px; margin: 15px 0; text-align: left; }
        .instruction-box h3 { margin-bottom: 10px; color: #fff; }
        .instruction-box ol { margin: 0; padding-left: 20px; line-height: 1.8; }
    </style>
</head>
<body>
    <div class="measurement-app">
        <div class="header">
            <h1>Measulor</h1>
            <p>AI Body Measurement System</p>
        </div>
        
        <div class="camera-box">
            <video id="video" autoplay playsinline></video>
            <canvas id="canvas"></canvas>
            
            <div class="instruction-box">
                <h3>📋 Instructions:</h3>
                <ol>
                    <li>Click "Start Camera" to begin</li>
                    <li>Position yourself 6-8 feet from camera</li>
                    <li>Stand straight with arms slightly away from body</li>
                    <li>Ensure good lighting</li>
                    <li>Click "Measure Now" to capture</li>
                </ol>
            </div>
            
            <div class="controls">
                <button class="btn-primary" id="startBtn" onclick="startCamera()">Start Camera</button>
                <button class="btn-secondary" id="captureBtn" onclick="capturePhoto()" style="display:none;">Measure Now</button>
                <button class="btn-secondary" id="switchBtn" onclick="switchCamera()" style="display:none;">🔄 Switch Camera</button>
            </div>
        </div>
        
        <div class="status" id="status">Ready to measure</div>
        <div class="results" id="results"></div>
    </div>

    <script>
        let currentStream = null;
        let currentFacingMode = 'user';

        async function startCamera() {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ video: true });
                const video = document.getElementById('video');
                video.srcObject = stream;
                currentStream = stream;
                document.getElementById('startBtn').style.display = 'none';
                document.getElementById('switchBtn').style.display = 'block';
                document.getElementById('captureBtn').style.display = 'block';
                document.getElementById('status').textContent = 'Camera ready - Click Measure Now to capture';
            } catch (error) {
                document.getElementById('status').textContent = 'Camera access denied';
            }
        }

        function capturePhoto() {
            const video = document.getElementById('video');
            const canvas = document.getElementById('canvas');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            canvas.getContext('2d').drawImage(video, 0, 0);
            
            document.getElementById('status').textContent = 'Processing measurements...';
            
            fetch('/api/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    image: canvas.toDataURL('image/jpeg', 0.8)
                })
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    const m = data.measurements;
                    document.getElementById('results').innerHTML = `
                        <h3>Your Measurements</h3>
                        <div class="measure-item"><span>Shoulder Width:</span><span>${m.shoulder_width} cm</span></div>
                        <div class="measure-item"><span>Hip Width:</span><span>${m.hip_width} cm</span></div>
                        <div class="measure-item"><span>Torso Length:</span><span>${m.torso_length} cm</span></div>
                        <div class="measure-item"><span>Arm Length:</span><span>${m.arm_length} cm</span></div>
                        <div class="measure-item"><span>Leg Length:</span><span>${m.leg_length} cm</span></div>
                        <div class="measure-item"><span>Est. Height:</span><span>${m.total_height} cm</span></div>
                        <div class="measure-item"><span>Body Shape:</span><span>${m.body_shape}</span></div>`;
                    document.getElementById('results').style.display = 'block';
                    document.getElementById('status').textContent = 'Measurement complete!';
                } else {
                    document.getElementById('status').textContent = 'Measurement failed. Please try again.';
                }
            })
            .catch(() => {
                document.getElementById('status').textContent = 'Error processing measurements';
            });
        }

        async function switchCamera() {
            if (currentStream) {
                currentStream.getTracks().forEach(track => track.stop());
            }
            currentFacingMode = currentFacingMode === 'user' ? 'environment' : 'user';
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ 
                    video: { facingMode: currentFacingMode }
                });
                const video = document.getElementById('video');
                video.srcObject = stream;
                currentStream = stream;
            } catch (error) {
                document.getElementById('status').textContent = 'Error switching camera';
            }
        }
    </script>
</body>
</html>
'''

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
        width, height = image.size
        
        measurements = {
            'shoulder_width': round(width * 0.28, 1),
            'hip_width': round(width * 0.25, 1),
            'torso_length': round(height * 0.35, 1),
            'arm_length': round(height * 0.38, 1),
            'leg_length': round(height * 0.52, 1)
        }
        measurements['total_height'] = round(measurements['torso_length'] + measurements['leg_length'], 1)
        ratio = measurements['shoulder_width'] / measurements['hip_width']
        if ratio > 1.05:
            body_shape = "Inverted Triangle"
        elif ratio < 0.95:
            body_shape = "Pear"
        else:
            body_shape = "Rectangle"
        measurements['body_shape'] = body_shape
        
        return jsonify({'success': True, 'measurements': measurements, 'message': 'Measurements calculated'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'message': 'Measulor API running'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
