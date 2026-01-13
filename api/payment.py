# Hybrid Payment System for Measulor
# Instamojo (Auto) + Manual UPI (Backup) - No PAN Required!    # Manual GPay UPI Payment - No PAN Required!
from flask import Blueprint, render_template_string, request, jsonify, redirect
import os
import secrets
import json
from datetime import datetime
import requests

payment_bp = Blueprint('payment', __name__)


# Your GPay UPI ID for manual payments (FREE - 0% fees)'UPI_ID', 'yourname@okaxis'    'GPAY_UPI_ID', 'yourname@oksbi'
YOUR_UPI_ID = os.getenv('UPI_ID', 'yourname@okaxis')  # Replace with your UPI ID

# Product Details
PRODUCT_PRICE = 499
PRODUCT_NAME = "Measulor Premium - Lifetime Access"

# Storage
orders_db = {}
licenses_db = {}

def generate_license_key():
    return f"MSL-{secrets.token_hex(8).upper()}"

# Payment Page with DUAL OPTIONS
PAYMENT_PAGE_HTML = '''<!DOCTYPE html>
<html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width,initial-scale=1">
            <title>Measulor Premium Payment</title>
            <style>
                * {
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                    font-family: -apple-system, sans-serif;
                }
                body {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    padding: 20px;
                }
                .container {
                    max-width: 600px;
                    margin: 0 auto;
                }
                .header {
                    text-align: center;
                    color: white;
                    margin-bottom: 30px;
                }
                .header h1 {
                    font-size: 32px;
                    margin-bottom: 10px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Measulor Premium</h1>
                    <p>Lifetime Access - ₹499</p>
                </div>
            </div>
        </body>
    </html>
    '''
# Flask Routes
@payment_bp.route('/payment')
def payment_page():
    return render_template_string(PAYMENT_PAGE_HTML, upi_id=YOUR_UPI_ID)



@payment_bp.route('/api/payment/manual', methods=['POST'])
def manual_upi_payment():
    """Handle manual UPI payment submission - FREE (0% fees)"""
    try:
        data = request.json
        email = data.get('email')
        name = data.get('name')
        transaction_id = data.get('transaction_id')
        
        if not email or not name or not transaction_id:
            return jsonify({
                'success': False,
                'message': 'All fields required'
            }), 400
        
        # Generate order ID
        order_id = 'MANUAL-' + secrets.token_hex(8).upper()
        
        # Store order for manual verification
        orders_db[order_id] = {
            'order_id': order_id,
            'email': email,
            'name': name,
            'transaction_id': transaction_id,
            'amount': PRODUCT_PRICE,
            'type': 'manual_upi',
            'status': 'pending_verification',
            'created_at': datetime.now().isoformat()
        }
        
        # Save to file
        try:
            with open('manual_orders.json', 'w') as f:
                json.dump(orders_db, f, indent=2)
        except:
            pass
        
        return jsonify({
            'success': True,
            'order_id': order_id,
            'message': 'Payment proof submitted. We will verify and email your license key within 2-4 hours.'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@payment_bp.route('/api/payment/instamojo-webhook', methods=['POST'])
def instamojo_webhook():
    """Handle Instamojo payment success webhook"""
    try:
        data = request.form
        payment_id = data.get('payment_id')
        payment_request_id = data.get('payment_request_id')
        status = data.get('status')
        
        if status == 'Credit' and payment_request_id in orders_db:
            # Payment successful - Generate license
            license_key = generate_license_key()
            
            orders_db[payment_request_id]['status'] = 'paid'
            orders_db[payment_request_id]['payment_id'] = payment_id
            orders_db[payment_request_id]['license_key'] = license_key
            
            licenses_db[license_key] = {
                'order_id': payment_request_id,
                'status': 'active',
                'created_at': datetime.now().isoformat()
            }
            
            # TODO: Send email with license key
        
        return jsonify({'status': 'ok'})
    
    except Exception as e:
        print(f'Webhook error: {e}')
        return jsonify({'error': str(e)}), 400

@payment_bp.route('/payment/success')
def payment_success():
    """Payment success page"""
    payment_id = request.args.get('payment_id')
    payment_request_id = request.args.get('payment_request_id')
    
    license_key = 'Processing...'
    if payment_request_id and payment_request_id in orders_db:
        order = orders_db[payment_request_id]
        license_key = order.get('license_key', 'Processing...')
    
    return render_template_string('''
        <!DOCTYPE html>
<html>
            <head>
                <meta charset="UTF-8">
                <title>Payment Successful</title>
                <style>
                    * {
                        margin: 0;
                        padding: 0;
                        box-sizing: border-box;
                        font-family: -apple-system, sans-serif;
                    }
                    body {
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        min-height: 100vh;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        padding: 20px;
                    }
                    .card {
                        background: white;
                        border-radius: 16px;
                        padding: 48px;
                        text-align: center;
                        max-width: 500px;
                        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    }
                    .success-icon {
                        font-size: 64px;
                        margin-bottom: 24px;
                    }
                    .title {
                        font-size: 28px;
                        font-weight: 700;
                        color: #1a202c;
                        margin-bottom: 12px;
                    }
                    .message {
                        color: #4a5568;
                        font-size: 16px;
                        margin-bottom: 32px;
                    }
                    .license-box {
                        background: #f7fafc;
                        border: 2px dashed #cbd5e0;
                        border-radius: 12px;
                        padding: 24px;
                        margin-bottom: 32px;
                    }
                    .license-label {
                        color: #718096;
                        font-size: 14px;
                        font-weight: 600;
                        margin-bottom: 8px;
                    }
                    .license-key {
                        font-size: 24px;
                        font-weight: 700;
                        color: #667eea;
                        font-family: monospace;
                        word-break: break-all;
                    }
                    .btn {
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        padding: 14px 32px;
                        border: none;
                        border-radius: 12px;
                        font-size: 16px;
                        font-weight: 600;
                        text-decoration: none;
                        display: inline-block;
                        margin: 8px;
                    }
                    .btn:hover {
                        transform: translateY(-2px);
                        box-shadow: 0 8px 16px rgba(102,126,234,0.4);
                    }
                </style>
            </head>
            <body>
                <div class="card">
                    <div class="success-icon">✅</div>
                    <h1 class="title">Payment Successful!</h1>
                    <p class="message">Your license key has been generated successfully.</p>
                    <div class="license-box">
                        <div class="license-label">YOUR LICENSE KEY</div>
                        <div class="license-key">{{ license_key }}</div>
                    </div>
                    <p style="color:#718096;font-size:14px;margin-bottom:24px">
                        Check your email for the license key and activation instructions.
                    </p>
                    <a href="/" class="btn">🏠 Go to Home</a>
                </div>
            </body>
        </html>
    ''', license_key=license_key)

@payment_bp.route('/api/payment/verify-manual/<order_id>', methods=['POST'])
def verify_manual_payment(order_id):
    """Admin endpoint to verify manual UPI payments"""
    # TODO: Add admin authentication
    if order_id in orders_db:
        license_key = generate_license_key()
        orders_db[order_id]['status'] = 'verified'
        orders_db[order_id]['license_key'] = license_key
        
        licenses_db[license_key] = {
            'order_id': order_id,
            'status': 'active',
            'created_at': datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True,
            'license_key': license_key
        })
    
    return jsonify({'success': False, 'message': 'Order not found'}), 404

@payment_bp.route('/api/payment/orders')
def get_orders():
    """View all orders (manual + automatic)"""
    return jsonify({'orders': orders_db})
