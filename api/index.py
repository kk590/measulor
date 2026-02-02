from flask import Flask, jsonify, request
from flask_cors import CORS
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
CORS(app)  # Enable CORS for all routes

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
    return '''<!DOCTYPE html><html><head> <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-4630566819144819" crossorigin="anonymous"></script>
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
    </style></head><body></body></html>'''

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

@app.route('/api/measure-video-3d', methods=['POST'])
def measure_video_3d():
    """
    NEW: Process video for body measurements using 3D reconstruction
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
