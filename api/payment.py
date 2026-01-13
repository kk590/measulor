# Manual UPI Payment Only - No PAN Required! 🇮🇳 Automatic Payment
from flask import Blueprint, render_template_string, request, jsonify, redirect

import os
import secrets
import json
from datetime import datetime
import requests

payment_bp = Blueprint('payment', __name__)

# Your GPay UPI ID for manual payments (FREE - 0% fees)'UPI_ID', 'yourname@okaxis')
YOUR_UPI_ID = os.getenv('UPI_ID', 'yourname@okaxis')  # Replace with your UPI ID
GPAY_UPI_ID = os.getenv('GPAY_UPI_ID', 'yourname@okbi')
PRODUCT_PRICE = "299"  # ₹299 INR
PRODUCT_NAME = "Measulor Premium"

# Database for storing orders and licenses
orders_db = {}
licenses_db = {}

def generate_license_key():
    return secrets.token_hex(16).upper()

# Payment Page HTML with GPay Integration
PAYMENT_PAGE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Measulor Premium - Payment</title>
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
        .header h1 {
            color: #764ba2;
            font-size: 28px;
            margin-bottom: 10px;
        }
        .price-tag {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 30px;
            border-radius: 50px;
            font-size: 32px;
            font-weight: bold;
            display: inline-block;
            margin: 20px 0;
        }
        .features {
            list-style: none;
            margin: 20px 0;
        }
        .features li {
            padding: 10px 0;
            border-bottom: 1px solid #eee;
            color: #555;
        }
        .features li:before {
            content: "✓";
            color: #667eea;
            font-weight: bold;
            margin-right: 10px;
        }
        .payment-section {
            margin-top: 30px;
        }
        .upi-button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 50px;
            font-size: 18px;
            font-weight: bold;
            cursor: pointer;
            width: 100%;
            margin: 10px 0;
            transition: transform 0.2s;
        }
        .upi-button:hover {
            transform: scale(1.05);
        }
        .upi-info {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
            display: none;
        }
        .upi-id {
            background: white;
            padding: 15px;
            border-radius: 5px;
            font-weight: bold;
            color: #764ba2;
            text-align: center;
            margin: 10px 0;
            border: 2px dashed #667eea;
        }
        .instructions {
            color: #666;
            font-size: 14px;
            line-height: 1.6;
        }
        .form-group {
            margin: 15px 0;
        }
        .form-group label {
            display: block;
            color: #555;
            margin-bottom: 5px;
            font-weight: 500;
        }
        .form-group input {
            width: 100%;
            padding: 12px;
            border: 2px solid #eee;
            border-radius: 5px;
            font-size: 16px;
        }
        .submit-btn {
            background: #28a745;
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 50px;
            font-size: 18px;
            font-weight: bold;
            cursor: pointer;
            width: 100%;
            margin-top: 20px;
        }
        .submit-btn:hover {
            background: #218838;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Measulor Premium</h1>
            <p>AI Body Measurement System</p>
            <div class="price-tag">₹299</div>
        </div>
        
        <ul class="features">
            <li>Unlimited AI body measurements</li>
            <li>Advanced accuracy algorithms</li>
            <li>Save measurement history</li>
            <li>Export detailed reports</li>
            <li>Priority customer support</li>
        </ul>
        
        <div class="payment-section">
            <button class="upi-button" onclick="showAutomaticPayment()">Pay with GPay/UPI</button>
            
            <div id="upi-info" class="upi-info">
                <h3 style="color: #764ba2; margin-bottom: 15px;">Pay using GPay/UPI</h3>
                <div class="upi-id">{{ upi_id }}</div>
                
                <div class="instructions">
                    <p><strong>Instructions:</strong></p>
                    <ol>
                        <li>Open Google Pay or any UPI app</li>
                        <li>Send ₹299 to the UPI ID above</li>
                        <li>Enter your transaction ID below</li>
                    </ol>
                </div>
                
                <form id="payment-form" onsubmit="submitPayment(event)">
                    <div class="form-group">
                        <label>Your Email:</label>
                        <input type="email" id="email" required placeholder="your@email.com">
                    </div>
                    <div class="form-group">
                        <label>UPI Transaction ID:</label>
                        <input type="text" id="txn_id" required placeholder="e.g., 123456789012">
                    </div>
                    <button type="submit" class="submit-btn">Verify Payment & Get License</button>
                </form>
            </div>
        </div>
    </div>
    
    <script>
        function showAutomaticPayment() {
            document.getElementById('upi-info').style.display = 'block';
        }
        
        function submitPayment(event) {
            event.preventDefault();
            
            const email = document.getElementById('email').value;
            const txn_id = document.getElementById('txn_id').value;
            
            fetch('/api/payment/verify', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    email: email,
                    transaction_id: txn_id,
                    amount: '299'
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Payment verified! Your license key: ' + data.license_key);
                    window.location.href = '/success?key=' + data.license_key;
                } else {
                    alert('Error: ' + data.message);
                }
            })
            .catch(error => {
                alert('Error processing payment. Please try again.');
            });
        }
    </script>
</body>
</html>
"""

@payment_bp.route('/')
def payment_page():
    return render_template_string(PAYMENT_PAGE_HTML, upi_id=YOUR_UPI_ID)

@payment_bp.route('/verify', methods=['POST'])
def verify_payment():
    data = request.get_json()
    email = data.get('email')
    transaction_id = data.get('transaction_id')
    amount = data.get('amount')
    
    # Generate order ID
    order_id = f"ORD_{datetime.now().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}"
    
    # Generate license key
    license_key = generate_license_key()
    
    # Store order
    orders_db[order_id] = {
        'email': email,
        'transaction_id': transaction_id,
        'amount': amount,
        'license_key': license_key,
        'timestamp': datetime.now().isoformat(),
        'status': 'pending_verification'
    }
    
    # Store license
    licenses_db[license_key] = {
        'email': email,
        'order_id': order_id,
        'activated': False,
        'created_at': datetime.now().isoformat()
    }
    
    return jsonify({
        'success': True,
        'license_key': license_key,
        'order_id': order_id,
        'message': 'Payment submitted for verification. Your license key has been generated!'
    })

@payment_bp.route('/check-license/<license_key>')
def check_license(license_key):
    if license_key in licenses_db:
        return jsonify({
            'valid': True,
            'license': licenses_db[license_key]
        })
    return jsonify({'valid': False}), 404
