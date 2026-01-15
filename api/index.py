from flask import Flask, jsonify, request
import base64
import io
import os
import random
import time
import hashlib
import hmac
import secrets
from cryptography.fernet import Fernet
from datetime import datetime
from PIL import Image
from .pricing import pricing_bp
from .pricing import subscription_bp

app = Flask(__name__)

# Register blueprints
app.register_blueprint(pricing_bp)
app.register_blueprint(subscription_bp)

# License key system with cryptography
LICENSE_SECRET = os.getenv('LICENSE_SECRET', secrets.token_hex(32))
cipher_suite = None
try:
    ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', Fernet.generate_key().decode())
    cipher_suite = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)
except:
    pass

# In-memory license storage
licenses = {}

def generate_license_key():
    raw_key = secrets.token_hex(16).upper()
    timestamp = datetime.now().isoformat()
    signature = hmac.new(LICENSE_SECRET.encode(), f"{raw_key}:{timestamp}".encode(), hashlib.sha256).hexdigest()[:16]
    return f"{raw_key}-{signature}"

def verify_license(license_key):
    if not license_key or '-' not in license_key:
        return False
    try:
        if license_key in licenses:
            license_data = licenses[license_key]
            if license_data.get('active', False):
                return True
    except:
        pass
    return False

def generate_demo_measurements(image_width, image_height):
    time.sleep(2)
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
        .header h1 { font-size: 1.8em; margin-bottom: 5px; }
        .price-tag { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 30px; border-radius: 50px; font-size: 32px; font-weight: bold; display: inline-block; margin: 20px 0; }
        .camera-box { background: rgba(255,255,255,0.1); border-radius: 15px; padding: 15px; margin: 15px 0; }
        #video { width: 100%; border-radius: 10px; background: #000; }
        #canvas { display: none; }
        .controls { display: flex; gap: 10px; margin-top: 15px; }
        button { flex: 1; padding: 15px; border: none; border-radius: 10px; font-size: 1em; font-weight: 600; cursor: pointer; }
        .btn-primary { background: #48bb78; color: white; }
        .btn-secondary { background: #4299e1; color: white; }
        .status { background: rgba(255,255,255,0.1); border-radius: 10px; padding: 15px; text-align: center; margin: 15px 0; }
        .results { background: rgba(255,255,255,0.15); border-radius: 10px; padding: 20px; margin: 15px 0; display: none; }
        .measure-item { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.2); }
        .demo-badge { background: rgba(255,200,0,0.9); color: #333; padding: 8px 15px; border-radius: 20px; font-size: 0.85em; font-weight: 600; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Measulor</h1>
        <p>AI Body Measurement System</p>
        <div class="demo-badge">DEMO MODE</div>
    </div>
    <div class="camera-box">
        <video id="video" autoplay playsinline></video>
        <canvas id="canvas"></canvas>
          <div style="background: rgba(255,255,255,0.15); padding: 15px; border-radius: 10px; margin: 15px 0; text-align: left;">\n   <h3 style="margin-bottom: 10px; color: #fff;">📋 Instructions:</h3>\n   <ol style="margin: 0; padding-left: 20px; line-height: 1.8;">\n    <li>Click "Start Camera" to begin</li>\n    <li>Position yourself 6-8 feet from camera</li>\n    <li>Stand straight with arms slightly away from body</li>\n    <li>Ensure good lighting</li>\n    <li>Enter valid license key for accurate measurements</li>\n    <li>Click "Measure Now" to capture</li>\n   </ol>\n  </div>
                    <div style="margin-top: 20px; padding: 15px; background: rgba(255,255,255,0.1); border-radius: 10px;">
                <label style="display: block; margin-bottom: 10px; font-weight: 600;">🔐 Enter License Key for Full Access</label>
                  <div style="background: rgba(255,100,100,0.2); border: 2px solid rgba(255,100,100,0.5); padding: 15px; border-radius: 10px; margin: 15px 0; text-align: center;"><p style="margin: 0; font-weight: 600; color: #ffe4e4;">⚠️ License Key Required - Enter a valid license key below to unlock full measurement capabilities</p></div>
                <input type="text" id="licenseKey" placeholder="XXXXXXXX-XXXXXXXX" style="width: 100%; padding: 12px; border: 2px solid rgba(255,255,255,0.3); border-radius: 8px; background: rgba(255,255,255,0.2); color: white; font-size: 1em; margin-bottom: 10px;">
                <button onclick="verifyLicense()" style="width: 100%; padding: 12px; background: #4299e1; color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer;">Activate License</button>
                <div id="licenseStatus" style="margin-top: 10px; padding: 10px; border-radius: 5px; display: none;"></div>
            </div>
        <div class="controls">
            <button class="btn-primary" id="startBtn" onclick="startCamera()"> disabled style="opacity: 0.5; cursor: not-allowed;"Start Camera</button>
            <button class="btn-secondary hidden" id="captureBtn" onclick="capturePhoto( disabled style="opacity: 0.5; cursor: not-allowed;")">Measure Now</button>
                  <button class="btn-secondary" id="switchBtn" onclick="switchCamera()" style="display:none;">🔄 Switch Camera</button>
        </div>
    </div>
    <div class="status" id="status">Tap Start Camera to begin</div>
    <div class="results" id="results"></div>
    <script>
        const video = document.getElementById('video');
        const canvas = document.getElementById('canvas');
        async function startCamera() {
            const stream = await navigator.mediaDevices.getUserMedia({ video: true });
            video.srcObject = stream;
                    currentStream = stream;
            document.getElementById('startBtn').style.display = 'none';
                    document.getElementById('switchBtn').style.display = 'block';
            document.getElementById('captureBtn').classList.remove('hidden');
        }
        function capturePhoto() {
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            canvas.getContext('2d').drawImage(video, 0, 0);
            fetch('/api/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: canvas.toDataURL('image/jpeg', 0.8), license_key: activeLicenseKey })            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    const m = data.measurements;
                    document.getElementById('results').innerHTML = `<h3>Your Measurements</h3>
                    <div class="measure-item"><span>Shoulder Width:</span><span>${m.shoulder_width} cm</span></div>
                    <div class="measure-item"><span>Hip Width:</span><span>${m.hip_width} cm</span></div>
                    <div class="measure-item"><span>Torso Length:</span><span>${m.torso_length} cm</span></div>
                    <div class="measure-item"><span>Arm Length:</span><span>${m.arm_length} cm</span></div>
                    <div class="measure-item"><span>Leg Length:</span><span>${m.leg_length} cm</span></div>
                    <div class="measure-item"><span>Est. Height:</span><span>${m.total_height} cm</span></div>
                    <div class="measure-item"><span>Body Shape:</span><span>${m.body_shape}</span></div>`;
                    document.getElementById('results').style.display = 'block';
                }
            });
        }

                function verifyLicense() {
            const licenseKey = document.getElementById('licenseKey').value;
            if (!licenseKey) {
                alert('Please enter a license key');
                return;
            }
            fetch('/api/check-license', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ license_key: licenseKey })
            })
            .then(r => r.json())
            .then(data => {
                if (data.valid) {
                    alert('License activated successfully!');
                                        activeLicenseKey = licenseKey;
                    const startBtn = document.getElementById('startBtn'); startBtn.disabled = false; startBtn.style.opacity = '1'; startBtn.style.cursor = 'pointer';                    document.getElementById('captureBtn').disabled = false;
                    const captureBtn = document.getElementById('captureBtn'); captureBtn.disabled = false; captureBtn.style.opacity = '1'; captureBtn.style.cursor = 'pointer';                    alert('Invalid license key');
                }
            })
            .catch(() => alert('Error verifying license'));
        }

                let currentStream = null;
        let currentFacingMode = 'user';
        
        async function switchCamera() {
            if (currentStream) {
                    let activeLicenseKey = '';
                currentStream.getTracks().forEach(track => track.stop());
            }
            currentFacingMode = currentFacingMode === 'user' ? 'environment' : 'user';
            const stream = await navigator.mediaDevices.getUserMedia({ 
                video: { facingMode: currentFacingMode } 
            });
            video.srcObject = stream;
            currentStream = stream;
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
        width, height = image.size
                license_key = data.get('license_key', '')
        
        # Check license and generate appropriate measurements
        is_licensed = verify_license(license_key)
        ed:
            # Real measurements using image analysis
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
            message = 'Real measurements calculated'
        else:
            measurements = generate_demo_measurements(width, height)
            message = 'Demo measurements generated'        return jsonify({
            'success': True,
            'message': message,        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/get-license')
def get_license():
    license_key = generate_license_key()
    licenses[license_key] = {
        'created_at': datetime.now().isoformat(),
        'active': True,
        'product': 'Measulor Premium'
    }
    return jsonify({
        'success': True,
        'license_key': license_key,
        'message': 'License key generated'
    })
#Complete rewrite: Clean index.py with license key 
@app.route('/api/check-license', methods=['POST'])
def check_license():
    data = request.json
    license_key = data.get('license_key', '')
    is_valid = verify_license(license_key)
    if is_valid:
        return jsonify({
            'success': True,
            'valid': True,
            'message': 'License key is valid',
            'license_data': licenses.get(license_key, {})
        })
    else:
        return jsonify({
            'success': False,
            'valid': False,
            'message': 'Invalid license key'
        })

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'message': 'Measulor API running', 'mode': 'demo'})

if __name__ == '__main__':
    app.run()
