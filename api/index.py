from flask import Flask, jsonify, request
import base64
import io
from PIL import Image

app = Flask(__name__)

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
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            color: white;
            overflow-x: hidden;
        }
        .header {
            padding: 15px 20px;
            text-align: center;
            background: rgba(0,0,0,0.2);
            backdrop-filter: blur(10px);
        }
        .header h1 {
            font-size: 1.8em;
            margin-bottom: 5px;
        }
        .header p {
            font-size: 0.9em;
            opacity: 0.9;
        }
        .container {
            flex: 1;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        .camera-container {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 15px;
            backdrop-filter: blur(10px);
        }
        #video {
            width: 100%;
            border-radius: 10px;
            background: #000;
            display: block;
        }
        #canvas {
            display: none;
        }
        .controls {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }
        button {
            flex: 1;
            padding: 15px;
            border: none;
            border-radius: 10px;
            font-size: 1em;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .btn-primary {
            background: #48bb78;
            color: white;
        }
        .btn-primary:active {
            background: #38a169;
            transform: scale(0.98);
        }
        .btn-secondary {
            background: #4299e1;
            color: white;
        }
        .btn-secondary:active {
            background: #3182ce;
            transform: scale(0.98);
        }
        .status {
            background: rgba(255,255,255,0.1);
            border-radius: 10px;
            padding: 15px;
            backdrop-filter: blur(10px);
            text-align: center;
            font-size: 0.9em;
        }
        .info-box {
            background: rgba(255,255,255,0.1);
            border-radius: 10px;
            padding: 15px;
            backdrop-filter: blur(10px);
        }
        .info-box h3 {
            margin-bottom: 10px;
            font-size: 1.1em;
        }
        .info-box p {
            font-size: 0.9em;
            line-height: 1.5;
            opacity: 0.95;
        }
        .hidden {
            display: none;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>👕 Measulor</h1>
        <p>AI Body Measurement Tool</p>
    </div>
    
    <div class="container">
        <div class="camera-container">
            <video id="video" autoplay playsinline></video>
            <canvas id="canvas"></canvas>
            <div class="controls">
                <button class="btn-primary" id="startBtn" onclick="startCamera()">Start Camera</button>
                <button class="btn-secondary hidden" id="captureBtn" onclick="capturePhoto()">Capture Photo</button>
            </div>
        </div>
        
        <div class="status" id="status">
            <p>Tap "Start Camera" to begin</p>
        </div>
        
        <div class="info-box">
            <h3>📱 Instructions</h3>
            <p>• Stand 6-8 feet from camera<br>
               • Ensure full body is visible<br>
               • Stand in T-pose for best results<br>
               • Make sure lighting is good</p>
        </div>
    </div>
    
    <script>
        const video = document.getElementById('video');
        const canvas = document.getElementById('canvas');
        const startBtn = document.getElementById('startBtn');
        const captureBtn = document.getElementById('captureBtn');
        const status = document.getElementById('status');
        let stream = null;
        
        async function startCamera() {
            try {
                status.innerHTML = '<p>Starting camera...</p>';
                
                stream = await navigator.mediaDevices.getUserMedia({
                    video: {
                        facingMode: 'user',
                        width: { ideal: 1280 },
                        height: { ideal: 720 }
                    }
                });
                
                video.srcObject = stream;
                startBtn.classList.add('hidden');
                captureBtn.classList.remove('hidden');
                status.innerHTML = '<p>✅ Camera active! Position yourself and tap Capture</p>';
            } catch (err) {
                console.error('Camera error:', err);
                status.innerHTML = '<p>❌ Camera access denied. Please allow camera permissions.</p>';
            }
        }
        
        function capturePhoto() {
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(video, 0, 0);
            
            const imageData = canvas.toDataURL('image/jpeg', 0.8);
            status.innerHTML = '<p>📸 Photo captured! Processing...</p>';
            
            // Send to backend
            fetch('/api/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image: imageData })
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    status.innerHTML = '<p>✅ Image received! (Processing pipeline coming soon)</p>';
                } else {
                    status.innerHTML = '<p>⚠️ ' + data.message + '</p>';
                }
            })
            .catch(err => {
                status.innerHTML = '<p>❌ Error processing image</p>';
                console.error(err);
            });
        }
        
        // Auto-start camera on mobile
        if (/Android|iPhone|iPad|iPod/i.test(navigator.userAgent)) {
            status.innerHTML = '<p>Mobile device detected! Tap "Start Camera" when ready.</p>';
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
        
        # Remove data URL prefix
        if 'base64,' in image_data:
            image_data = image_data.split('base64,')[1]
        
        # Decode base64 image
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))
        
        # Get image dimensions
        width, height = image.size
        
        return jsonify({
            'success': True,
            'message': 'Image received successfully',
            'dimensions': {'width': width, 'height': height}
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'message': 'Mobile app is running!'})

if __name__ == '__main__':
    app.run()
