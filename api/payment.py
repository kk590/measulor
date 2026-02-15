# Manual UPI Payment Only - No PAN Required! 🇮🇳 Automatic Payment
from flask import Blueprint, render_template_string, request, jsonify, redirect

import os
import secrets
import json
from datetime import datetime
import requests
import hashlib
import hmac
from cryptography.fernet import Fernet

# Cryptographic security configuration
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', Fernet.generate_key().decode())  # Generate in production
SECRET_KEY = os.getenv('SECRET_KEY', secrets.token_hex(32))  # For HMAC signing
cipher = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)

# Database for storing orders and licenses
orders_db = {}
licenses_db = {}

def generate_license_key():
    """Generate cryptographically secure license key with encryption"""
    raw_key = secrets.token_hex(16).upper()
    # Add timestamp and hash for extra security
    timestamp = datetime.now().isoformat()
    data = f"{raw_key}:{timestamp}"
    encrypted = cipher.encrypt(data.encode()).decode()
    return encrypted[:32]  # Return first 32 chars of encrypted key


# Payment Page HTML with GPay Integration
PAYMENT_PAGE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Measulor Premium - License Activation</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 20px;
            padding: 40px;
            max-width: 500px;
            width: 100%;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .icon {
            width: 80px;
            height: 80px;
            margin: 0 auto 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 40px;
        }
        .header h1 {
            color: #764ba2;
            font-size: 28px;
            margin-bottom: 10px;
        }
        .header p {
            color: #666;
            font-size: 16px;
        }
        .features {
            list-style: none;
            margin: 20px 0;
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
        }
        .features li {
            padding: 8px 0;
            color: #555;
            font-size: 14px;
        }
        .features li:before {
            content: "✓";
            color: #667eea;
            font-weight: bold;
            margin-right: 10px;
        }
        .activation-section {
            margin-top: 30px;
        }
        .form-group {
            margin: 20px 0;
        }
        .form-group label {
            display: block;
            color: #555;
            margin-bottom: 8px;
            font-weight: 500;
            font-size: 14px;
        }
        .form-group input {
            width: 100%;
            padding: 15px;
            border: 2px solid #eee;
            border-radius: 10px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        .form-group input[type="text"] {
            font-family: 'Courier New', monospace;
            letter-spacing: 2px;
            text-transform: uppercase;
        }
        .form-group input:focus {
            outline: none;
            border-color: #667eea;
        }
        .help-text {
            color: #999;
            font-size: 12px;
            margin-top: 5px;
        }
        .activate-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 50px;
            font-size: 18px;
            font-weight: bold;
            cursor: pointer;
            width: 100%;
            margin-top: 10px;
            transition: transform 0.2s;
        }
        .activate-btn:hover {
            transform: scale(1.02);
        }
        .activate-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        .status-message {
            margin-top: 20px;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            display: none;
            animation: slideIn 0.3s ease;
        }
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(-10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        .status-message.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .status-message.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255,255,255,.3);
            border-radius: 50%;
            border-top-color: white;
            animation: spin 1s ease-in-out infinite;
            margin-left: 10px;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="icon">🔑</div>
            <h1>Activate Measulor Premium</h1>
            <p>Enter your license key to unlock premium features</p>
        </div>
        
        <ul class="features">
            <li>Unlimited AI body measurements</li>
            <li>Advanced accuracy algorithms</li>
            <li>Save measurement history</li>
            <li>Export detailed reports</li>
            <li>Priority customer support</li>
        </ul>
        
        <div class="activation-section">
            <form id="activation-form" onsubmit="activateLicense(event)">
                <div class="form-group">
                    <label>License Key:</label>
                    <input 
                        type="text" 
                        id="license_key" 
                        required 
                        placeholder="Enter your license key"
                        maxlength="128"
                        oninput="formatLicenseKey(this)"
                        autofocus
                    >
                    <div class="help-text">Paste your full license key as provided in your email</div>
                </div>
                
                <button type="submit" class="activate-btn" id="activate-btn">
                    Activate License
                </button>
            </form>
            
            <div id="status-message" class="status-message"></div>
        </div>
    </div>
    
    <script>
        function formatLicenseKey(input) {
            // Keep user-provided grouping, only normalize whitespace.
            input.value = input.value.replace(/\s+/g, '').trim();
        }
        
        function showStatus(message, isSuccess) {
            const statusDiv = document.getElementById('status-message');
            statusDiv.textContent = message;
            statusDiv.className = 'status-message ' + (isSuccess ? 'success' : 'error');
            statusDiv.style.display = 'block';
            
            if (isSuccess) {
                setTimeout(() => {
                    statusDiv.style.display = 'none';
                }, 5000);
            }
        }
        
        function activateLicense(event) {
            event.preventDefault();
            
            const licenseKey = document.getElementById('license_key').value;
            const submitBtn = document.getElementById('activate-btn');
            
            // Keep client-side check permissive; server-side validation is authoritative.
            if (!/^[A-Za-z0-9-]{8,128}$/.test(licenseKey) || licenseKey.startsWith('-') || licenseKey.endsWith('-') || licenseKey.includes('--')) {
                showStatus('Invalid license key format', false);
                return;
            }
            
            // Disable button and show loading
            submitBtn.disabled = true;
            submitBtn.innerHTML = 'Activating<span class="loading"></span>';
            
            // Keygen API configuration
            const KEYGEN_ACCOUNT_ID = 'YOUR_ACCOUNT_ID'; // Replace with your Keygen account ID
            const KEYGEN_PRODUCT_ID = 'YOUR_PRODUCT_ID'; // Replace with your product ID (optional)
            
            // Validate license with Keygen
            fetch(`https://api.keygen.sh/v1/accounts/${KEYGEN_ACCOUNT_ID}/licenses/actions/validate-key`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/vnd.api+json',
                    'Accept': 'application/vnd.api+json'
                },
                body: JSON.stringify({
                    meta: {
                        key: licenseKey
                    }
                })
            })
            .then(response => response.json())
            .then(data => {
                submitBtn.disabled = false;
                submitBtn.innerHTML = 'Activate License';
                
                if (data.meta && data.meta.valid === true) {
                    // License is valid
                    const license = data.data;
                    showStatus('License activated successfully! Redirecting...', true);
                    
                    // Store license info (you can customize this)
                    localStorage.setItem('measulor_license', JSON.stringify({
                        key: licenseKey,
                        id: license.id,
                        activated: true,
                        activatedAt: new Date().toISOString()
                    }));
                    
                    setTimeout(() => {
                        window.location.href = '/dashboard';
                    }, 2000);
                } else {
                    // License is invalid
                    const errorMsg = data.meta && data.meta.detail 
                        ? data.meta.detail 
                        : 'Invalid license key. Please check and try again.';
                    showStatus(errorMsg, false);
                }
            })
            .catch(error => {
                submitBtn.disabled = false;
                submitBtn.innerHTML = 'Activate License';
                showStatus('Error validating license. Please try again.', false);
                console.error('Keygen validation error:', error);
            });
        }
    </script>
</body>
</html>
"""


payment_bp = Blueprint('payment', __name__)


@payment_bp.route('/')
def payment_portal():
    return render_template_string(PAYMENT_PAGE_HTML)


def decrypt_data(encrypted_data: str) -> str:
    """Decrypt encrypted data"""
    try:
        return cipher.decrypt(encrypted_data.encode()).decode()
    except:
        return None

def generate_hmac_signature(data: str) -> str:
    """Generate HMAC signature for data integrity verification"""
    return hmac.new(SECRET_KEY.encode(), data.encode(), hashlib.sha256).hexdigest()

def verify_hmac_signature(data: str, signature: str) -> bool:
    """Verify HMAC signature"""
    expected_signature = generate_hmac_signature(data)
    return hmac.compare_digest(expected_signature, signature)

@payment_bp.route('/check-license/<license_key>')
def check_license(license_key):
    if license_key in licenses_db:
        return jsonify({
            'valid': True,
            'license': licenses_db[license_key]
        })
    return jsonify({'valid': False}), 404
