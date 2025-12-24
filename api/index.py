from flask import Flask, jsonify, request
import base64
import io
import random
import time
from PIL import Image

app = Flask(__name__)

def generate_demo_measurements(image_width, image_height):
    """Generate realistic demo measurements based on image dimensions"""
    time.sleep(2)  # Simulate processing time
    
    # Generate realistic measurements
    measurements = {
        'shoulder_width': round(random.uniform(38.0, 50.0), 1),
        'hip_width': round(random.uniform(32.0, 42.0), 1),
        'torso_length': round(random.uniform(55.0, 70.0), 1),
        'arm_length': round(random.uniform(55.0, 65.0), 1),
        'leg_length': round(random.uniform(85.0, 105.0), 1)
    }
    
    # Calculate total height
    measurements['total_height'] = round(measurements['torso_length'] + measurements['leg_length'], 1)
    
    # Determine body shape
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
        .demo-badge { background: rgba(255,200,0,0.9); color: #333; padding: 8px 15px; border-radius: 20px; font-size: 0.85em; font-weight: 600; margin: 10px auto; display: inline-block; }
    </style>
</head>
<body>
    <div class="header">
        <h1>👕 Measulor</h1>
        <p>AI Body Measurement Tool</p>
        <div class="demo-badge">🌟 DEMO MODE - Simulated Measurements</div>
                        <a href="#pricing" class="upgrade-btn" style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 12px 30px; border-radius: 25px; text-decoration: none; font-weight: 600; margin-left: 15px; font-size: 0.9em; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4); transition: transform 0.2s;">💎 Upgrade to Premium</a>
    </div>
    <div class="camera-box">
        <video id="video" autoplay playsinline></video>
        <canvas id="canvas"></canvas>
        <div class="controls">
            <button class="btn-primary" id="startBtn" onclick="startCamera()">Start Camera</button>
                            <button class="btn-secondary" id="switchBtn" style="display:none;" onclick="switchCamera()">🔄 Switch Camera</button>
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
                const switchBtn = document.getElementById('switchBtn');
        let currentFacingMode = 'user'; // 'user' for front camera, 'environment' for back camera
        let currentStream = null;

        const results = document.getElementById('results');
        async function startCamera() {
            try {
            const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: currentFacingMode, width: { ideal: 1280 }, height: { ideal: 720 } } });                video.srcObject = stream;
                startBtn.classList.add('hidden');
                            currentStream = stream;
                captureBtn.classList.remove('hidden');
                status.innerHTML = '✅ Camera active! Stand in T-pose and tap Measure';
                            switchBtn.style.display = 'inline-block';
            } catch (err) { status.innerHTML = '❌ Camera access denied'; }
        }
        function capturePhoto() {
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            canvas.getContext('2d').drawImage(video, 0, 0);
            status.innerHTML = '<div class="loading"></div> Processing AI measurements... (2-3 seconds)';
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
                    status.innerHTML = '✅ Measurements complete! 🎉';
                } else {
                    status.innerHTML = '❌ ' + (data.message || 'Processing error');
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

        async function switchCamera() {
            // Stop current stream
            if (currentStream) {
                currentStream.getTracks().forEach(track => track.stop());
            }
            
            // Toggle facing mode
            currentFacingMode = currentFacingMode === 'user' ? 'environment' : 'user';
            
            // Restart camera with new facing mode
            await startCamera();
        }

    </script>

        <!-- Pricing Section -->
    <div id="pricing" style="max-width: 900px; margin: 60px auto; padding: 40px 20px; background: rgba(255,255,255,0.05); border-radius: 20px; backdrop-filter: blur(10px);">
        <h2 style="text-align: center; font-size: 2.5em; margin-bottom: 15px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">💎 Upgrade to Premium</h2>
        <p style="text-align: center; font-size: 1.1em; color: rgba(255,255,255,0.8); margin-bottom: 40px;">Get AI-powered body measurements with lifetime access</p>
        
        <div style="background: rgba(255,255,255,0.1); border-radius: 15px; padding: 35px; max-width: 500px; margin: 0 auto; border: 2px solid rgba(102, 126, 234, 0.3);">
            <div style="text-align: center; margin-bottom: 25px;">
                <div style="font-size: 3.5em; font-weight: 700; color: #fff;">$5.99</div>
                <div style="font-size: 1.1em; color: rgba(255,255,255,0.7); margin-top: 5px;">One-time payment • Lifetime access</div>
            </div>
            
            <div style="text-align: left; margin: 25px 0; font-size: 1em;">
                <div style="margin: 12px 0; padding-left: 25px; position: relative;">
                    <span style="position: absolute; left: 0;">✅</span> Real AI-powered measurements (MediaPipe)
                </div>
                <div style="margin: 12px 0; padding-left: 25px; position: relative;">
                    <span style="position: absolute; left: 0;">✅</span> Shoulders, Chest, Waist, Hips, Arms, Legs
                </div>
                <div style="margin: 12px 0; padding-left: 25px; position: relative;">
                    <span style="position: absolute; left: 0;">✅</span> Save & track measurement history
                </div>
                <div style="margin: 12px 0; padding-left: 25px; position: relative;">
                    <span style="position: absolute; left: 0;">✅</span> Export measurements as CSV/PDF
                </div>
                <div style="margin: 12px 0; padding-left: 25px; position: relative;">
                    <span style="position: absolute; left: 0;">✅</span> Mobile-friendly camera interface
                </div>
                <div style="margin: 12px 0; padding-left: 25px; position: relative;">
                    <span style="position: absolute; left: 0;">✅</span> No subscription • Pay once, use forever
                </div>
            </div>
            
            <a href="https://gum.co/measulor" target="_blank" style="display: block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 18px; border-radius: 12px; text-align: center; text-decoration: none; font-weight: 700; font-size: 1.2em; margin-top: 25px; box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5); transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">🚀 Get Premium Access Now</a>
            
            <p style="text-align: center; font-size: 0.85em; color: rgba(255,255,255,0.5); margin-top: 15px;">Instant access after payment via Gumroad</p>
        </div>
    </div>
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
        width, height = image.size
        measurements = generate_demo_measurements(width, height)
        return jsonify({
            'success': True,
            'message': 'Demo measurements generated',
            'measurements': measurements,
            'note': 'Demo version - Real AI processing available on production server'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'message': 'Measulor Demo API running!', 'mode': 'demo'})

if __name__ == '__main__':
    app.run()
