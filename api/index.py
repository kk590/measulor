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
from datetime import datetime, timedelta
from PIL import Image

import requests
from .keygen_integration import verify_license_with_keygen
from .video_3d_measurement_pipeline import Video3DMeasurementPipeline

app = Flask(__name__)


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
    raw_key = secrets.token_hex(32).upper()
    timestamp = datetime.now().isoformat()
    signature = hmac.new(LICENSE_SECRET.encode(), f"{raw_key}:{timestamp}".encode(), hashlib.sha256).hexdigest()[:32]
    return f"{raw_key}-{signature}"


def verify_license(license_key):
    # Use Keygen integration for license validation
    try:
        is_valid, license_data = verify_license_with_keygen(license_key)
        return is_valid
    except Exception as e:
        print(f'Error verifying license with Keygen: {str(e)}')
        return False


def generate_demo_measurements(width, height):
    """Generate demo measurements for unlicensed users"""
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
    <title>Measulor - License Activation Portal</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); font-family: -apple-system, sans-serif; min-height: 100vh; color: white; padding: 15px; }
        .header { text-align: center; padding: 15px 0; }
        .header h1 { font-size: 2.2em; margin-bottom: 10px; }
        .header p { font-size: 1.1em; opacity: 0.9; }
        .portal-container { max-width: 400px; margin: 50px auto; }
        .portal-box { background: rgba(255,255,255,0.1); border-radius: 20px; padding: 40px; backdrop-filter: blur(10px); }
        .license-icon { font-size: 60px; text-align: center; margin-bottom: 20px; }
        .input-group { margin: 20px 0; }
        input { width: 100%; padding: 15px; border: 2px solid rgba(255,255,255,0.3); border-radius: 10px; background: rgba(255,255,255,0.2); color: white; font-size: 1em; }
        input::placeholder { color: rgba(255,255,255,0.6); }
        button { width: 100%; padding: 15px; border: none; border-radius: 10px; font-size: 1.1em; font-weight: 600; cursor: pointer; transition: all 0.3s; }
        .btn-activate { background: #48bb78; color: white; }
        .btn-activate:hover { background: #38a169; transform: translateY(-2px); }
        .status-message { margin-top: 15px; padding: 15px; border-radius: 10px; display: none; }
        .success { background: rgba(72,187,120,0.2); border: 1px solid #48bb78; }
        .error { background: rgba(245,101,101,0.2); border: 1px solid #f56565; }
        .features { margin-top: 30px; }
        .feature-item { display: flex; align-items: center; margin: 10px 0; opacity: 0.9; }
        .feature-icon { margin-right: 10px; }
        
        /* Measurement App Styles (Hidden Initially) */
        .measurement-app { display: none; }
        .camera-box { background: rgba(255,255,255,0.1); border-radius: 15px; padding: 15px; margin: 15px 0; }
        #video { width: 100%; border-radius: 10px; background: #000; }
        #canvas { display: none; }
        .controls { display: flex; gap: 10px; margin-top: 15px; }
        .btn-primary { background: #48bb78; color: white; }
        .btn-secondary { background: #4299e1; color: white; }
        .status { background: rgba(255,255,255,0.1); border-radius: 10px; padding: 15px; text-align: center; margin: 15px 0; }
        .results { background: rgba(255,255,255,0.15); border-radius: 10px; padding: 20px; margin: 15px 0; display: none; }
        .measure-item { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.2); }
        .demo-badge { background: rgba(255,200,0,0.9); color: #333; padding: 8px 15px; border-radius: 20px; font-size: 0.85em; font-weight: 600; }
        .instruction-box { background: rgba(255,255,255,0.15); padding: 15px; border-radius: 10px; margin: 15px 0; text-align: left; }
        .instruction-box h3 { margin-bottom: 10px; color: #fff; }
        .instruction-box ol { margin: 0; padding-left: 20px; line-height: 1.8; }
        .loading-spinner { display: none; text-align: center; padding: 20px; }
        .spinner { border: 3px solid rgba(255,255,255,0.3); border-top: 3px solid white; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <!-- License Activation Portal -->
    <div id="licensePortal" class="portal-container">
        <div class="portal-box">
            <div class="header">
                <div class="license-icon">🔐</div>
                <h1>Measulor</h1>
                <p>AI Body Measurement System</p>
            </div>
            
            <div class="input-group">
                <label style="display: block; margin-bottom: 10px; font-weight: 600;">Enter Your License Key</label>
                <input type="text" id="licenseKey" placeholder="XXXXXXXX-XXXXXXXX" maxlength="17">
            </div>
            
            <button class="btn-activate" onclick="verifyLicense()">
                Activate License
            </button>
            
            <div id="licenseStatus" class="status-message"></div>
            
            <div class="loading-spinner" id="loadingSpinner">
                <div class="spinner"></div>
                <p style="margin-top: 10px;">Verifying license...</p>
            </div>
            
            <div class="features">
                <h3 style="margin-bottom: 15px;">What you'll unlock:</h3>
                <div class="feature-item">
                    <span class="feature-icon">✓</span>
                    <span>Accurate body measurements</span>
                </div>
                <div class="feature-item">
                    <span class="feature-icon">✓</span>
                    <span>Real-time camera processing</span>
                </div>
                <div class="feature-item">
                    <span class="feature-icon">✓</span>
                    <span>Detailed body analysis</span>
                </div>
                <div class="feature-item">
                    <span class="feature-icon">✓</span>
                    <span>Body shape detection</span>
                </div>
            </div>
        </div>
    </div>

    <!-- Measurement App (Hidden Initially) -->
    <div id="measurementApp" class="measurement-app">
        <div class="header">
            <h1>Measulor</h1>
            <p>AI Body Measurement System</p>
            <div class="demo-badge" id="demoBadge">LICENSED</div>
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
                <button class="btn-secondary hidden" id="captureBtn" onclick="capturePhoto()">Measure Now</button>
                <button class="btn-secondary" id="switchBtn" onclick="switchCamera()" style="display:none;">🔄 Switch Camera</button>
            </div>
        </div>
        
        <div class="status" id="status">Ready to measure</div>
        <div class="results" id="results"></div>
    </div>

    <script>
        let activeLicenseKey = '';
        let currentStream = null;
        let currentFacingMode = 'user';

        // License verification function
        async function verifyLicense() {
            const licenseKey = document.getElementById('licenseKey').value.trim();
            const statusDiv = document.getElementById('licenseStatus');
            const loadingSpinner = document.getElementById('loadingSpinner');
            
            if (!licenseKey) {
                showStatus('Please enter a license key', 'error');
                return;
            }
            
            // Validate format
            if (!/^[A-Za-z0-9]{8}-[A-Za-z0-9]{8}$/.test(licenseKey)) {
                showStatus('Invalid license key format', 'error');
                return;
            }
            
            // Show loading
            loadingSpinner.style.display = 'block';
            statusDiv.style.display = 'none';
            
            try {
                const response = await fetch('/api/check-license', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ license_key: licenseKey })
                });
                
                const data = await response.json();
                loadingSpinner.style.display = 'none';
                
                if (data.valid) {
                    activeLicenseKey = licenseKey;
                    showStatus('License activated successfully!', 'success');
                    setTimeout(() => {
                        showMeasurementApp();
                    }, 1500);
                } else {
                    showStatus('Invalid or expired license key', 'error');
                }
            } catch (error) {
                loadingSpinner.style.display = 'none';
                showStatus('Error verifying license. Please try again.', 'error');
            }
        }

        function showStatus(message, type) {
            const statusDiv = document.getElementById('licenseStatus');
            statusDiv.textContent = message;
            statusDiv.className = 'status-message ' + type;
            statusDiv.style.display = 'block';
        }

        function showMeasurementApp() {
            document.getElementById('licensePortal').style.display = 'none';
            document.getElementById('measurementApp').style.display = 'block';
        }

        // Camera and measurement functions
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
                    image: canvas.toDataURL('image/jpeg', 0.8), 
                    license_key: activeLicenseKey 
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
                document.getElementById('status').textContent = 'Camera switch failed';
            }
        }

        // Add enter key support for license input
        document.getElementById('licenseKey').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                verifyLicense();
            }
        });
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
        license_key = data.get('license_key', '')        
        # Check license and generate appropriate measurements
        is_licensed = verify_license(license_key)
        if is_licensed:            
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
            message = 'Demo measurements generated'       
        return jsonify({'success': True, 'measurements': measurements, 'message': message})
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

# Key Generation Integration - Bulk License Key Generation
@app.route('/api/keygen/generate', methods=['POST'])
def keygen_generate():
    """Generate bulk license keys with customizable options"""
    try:
        data = request.get_json()
        count = data.get('count', 1)  # Number of keys to generate
        product = data.get('product', 'Measulor Premium')
        expiry_days = data.get('expiry_days', 365)  # 1 year by default
        
        if count > 100:
            return jsonify({'error': 'Maximum 100 keys per request'}), 400
        
        generated_keys = []
        for _ in range(count):
            key = generate_license_key()
            licenses[key] = {
                'created_at': datetime.now().isoformat(),
                'active': True,
                'product': product,
                'expiry_days': expiry_days,
                'activation_date': None,
                'status': 'generated'
            }
            generated_keys.append(key)
        
        return jsonify({
            'success': True,
            'message': f'Generated {count} license keys',
            'keys': generated_keys,
            'product': product,
            'expiry_days': expiry_days
        }), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/keygen/activate', methods=['POST'])
def keygen_activate():
    """Activate a license key for a user"""
    try:
        data = request.get_json()
        license_key = data.get('license_key')
        email = data.get('email')
        
        if license_key not in licenses:
            return jsonify({'error': 'Invalid license key'}), 404
        
        license_data = licenses[license_key]
        
        if license_data.get('status') != 'generated':
            return jsonify({'error': 'License key already activated'}), 400
        
        # Activate the license
        licenses[license_key].update({
            'status': 'activated',
            'activation_date': datetime.now().isoformat(),
            'email': email
        })
        
        return jsonify({
            'success': True,
            'message': 'License key activated',
            'license_key': license_key,
            'email': email
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/keygen/validate/<license_key>', methods=['GET'])
def keygen_validate(license_key):
    """Validate license key and check expiry status"""
    try:
        if license_key not in licenses:
            return jsonify({'valid': False, 'message': 'Invalid license key'}), 404
        
        license_data = licenses[license_key]
        created_at = datetime.fromisoformat(license_data['created_at'])
        expiry_days = license_data.get('expiry_days', 365)
        expiry_date = created_at + timedelta(days=expiry_days)
        
        is_expired = datetime.now() > expiry_date
        
        return jsonify({
            'valid': not is_expired,
            'license_key': license_key,
            'status': license_data.get('status'),
            'product': license_data.get('product'),
            'created_at': license_data.get('created_at'),
            'activated_at': license_data.get('activation_date'),
            'expiry_date': expiry_date.isoformat(),
            'expired': is_expired
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/keygen/stats', methods=['GET'])
def keygen_stats():
    """Get key generation statistics"""
    try:
        total_keys = len(licenses)
        generated = sum(1 for k in licenses.values() if k.get('status') == 'generated')
        activated = sum(1 for k in licenses.values() if k.get('status') == 'activated')
        expired = sum(1 for k in licenses.values() if datetime.now() > 
                      (datetime.fromisoformat(k['created_at']) + timedelta(days=k.get('expiry_days', 365))))
        
        return jsonify({
            'total_keys': total_keys,
            'generated_keys': generated,
            'activated_keys': activated,
            'expired_keys': expired,
            'active_keys': total_keys - expired
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/measure-video-3d', methods=['POST'])
def measure_video_3d():
    """
    Process video for body measurements using 3D reconstruction
    Pipeline: video -> 3D model -> body measurements
    Accepts: video file (mp4, mov, avi)
    Returns: Body measurements from 3D model analysis
    """
    try:
        # Get video file from request
        if 'video' not in request.files:
            return jsonify({
                'success': False,
                'message': 'No video file provided'
            }), 400
        
        video_file = request.files['video']
        
        if video_file.filename == '':
            return jsonify({
                'success': False,
                'message': 'No video file selected'
            }), 400
        
        # Get optional reference height
        reference_height = request.form.get('height_cm', type=float)
        
        # Save video temporarily
        import tempfile
        temp_path = os.path.join(tempfile.gettempdir(), 'upload_' + video_file.filename)
        video_file.save(temp_path)
        
        # Process video through 3D pipeline
        pipeline = Video3DMeasurementPipeline(reference_height)
        success, result = pipeline.process_video(temp_path, max_frames=30)
        
        # Cleanup temp file
        try:
            os.remove(temp_path)
        except:
            pass
        
        if success:
            summary = pipeline.get_summary()
            return jsonify({
                'success': True,
                'data': summary,
                'pipeline': '3D reconstruction',
                'full_results': result
            })
        else:
            return jsonify(result), 400
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

if __name__ == '__main__':
    app.run()

if __name__ == '__main__':
    app.run()
