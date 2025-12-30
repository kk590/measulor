# Razorpay Payment Integration for Measulor
# Professional payment gateway with GPay, UPI, Cards support

from flask import Blueprint, render_template_string, request, jsonify, redirect
import os
import hmac
import hashlib
import secrets
import json
from datetime import datetime

# Note: Install razorpay SDK: pip install razorpay
try:
    import razorpay
except ImportError:
    razorpay = None
    print("WARNING: Razorpay SDK not installed. Run: pip install razorpay")

payment_bp = Blueprint('payment', __name__)

# Razorpay Credentials (IMPORTANT: Replace with your actual keys)
# Get these from: https://dashboard.razorpay.com/app/keys
RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID', 'rzp_test_YOUR_KEY_ID')  # Test key
RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET', 'YOUR_KEY_SECRET')

# Initialize Razorpay Client
if razorpay:
    razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
else:
    razorpay_client = None

# In-memory storage (replace with database in production)
orders_db = {}
licenses_db = {}

# Pricing
PRODUCT_PRICE = 49900  # ₹499 in paise (Razorpay uses paise)
PRODUCT_NAME = "Measulor Premium - Lifetime Access"

def generate_license_key():
    """Generate a unique license key"""
    return f"MSL-{secrets.token_hex(8).upper()}"

# Professional Payment Page HTML (ChatGPT/Gemini style)
PAYMENT_PAGE_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Upgrade to Measulor Premium</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: -apple-system, system-ui, sans-serif; }
        body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }
        .container { max-width: 480px; width: 100%; }
        .card { background: white; border-radius: 16px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); overflow: hidden; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 32px 24px; text-align: center; }
        .header h1 { font-size: 24px; font-weight: 600; margin-bottom: 8px; }
        .header p { opacity: 0.9; font-size: 14px; }
        .content { padding: 32px 24px; }
        .price { text-align: center; margin-bottom: 32px; }
        .price-amount { font-size: 48px; font-weight: 700; color: #1a202c; }
        .price-period { color: #718096; font-size: 16px; margin-top: 4px; }
        .features { margin-bottom: 32px; }
        .feature { display: flex; align-items: flex-start; padding: 12px 0; border-bottom: 1px solid #e2e8f0; }
        .feature:last-child { border-bottom: none; }
        .feature-icon { color: #48bb78; font-size: 20px; margin-right: 12px; flex-shrink: 0; }
        .feature-text { color: #4a5568; font-size: 15px; line-height: 1.5; }
        .btn-upgrade { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; width: 100%; padding: 16px; border: none; border-radius: 12px; font-size: 16px; font-weight: 600; cursor: pointer; transition: transform 0.2s, box-shadow 0.2s; }
        .btn-upgrade:hover { transform: translateY(-2px); box-shadow: 0 12px 24px rgba(102, 126, 234, 0.4); }
        .btn-upgrade:active { transform: translateY(0); }
        .secure { text-align: center; margin-top: 20px; color: #a0aec0; font-size: 13px; }
        .payment-methods { display: flex; justify-content: center; gap: 12px; margin-top: 16px; flex-wrap: wrap; }
        .payment-method { background: #f7fafc; padding: 8px 16px; border-radius: 8px; font-size: 12px; color: #4a5568; font-weight: 500; }
        .loading { display: none; text-align: center; padding: 20px; }
        .spinner { border: 3px solid #f3f3f3; border-top: 3px solid #667eea; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <div class="header">
                <h1>👕 Measulor Premium</h1>
                <p>Upgrade to unlock AI-powered body measurements</p>
            </div>
            <div class="content">
                <div class="price">
                    <div class="price-amount">₹499</div>
                    <div class="price-period">One-time payment • Lifetime access</div>
                </div>
                <div class="features">
                    <div class="feature">
                        <div class="feature-icon">✓</div>
                        <div class="feature-text">Real AI-powered measurements using MediaPipe</div>
                    </div>
                    <div class="feature">
                        <div class="feature-icon">✓</div>
                        <div class="feature-text">Measure shoulders, chest, waist, hips, arms, legs</div>
                    </div>
                    <div class="feature">
                        <div class="feature-icon">✓</div>
                        <div class="feature-text">Save & track measurement history</div>
                    </div>
                    <div class="feature">
                        <div class="feature-icon">✓</div>
                        <div class="feature-text">Export as CSV/PDF reports</div>
                    </div>
                    <div class="feature">
                        <div class="feature-icon">✓</div>
                        <div class="feature-text">Mobile-friendly camera interface</div>
                    </div>
                </div>
                <button id="rzp-button" class="btn-upgrade" onclick="initiatePayment()">
                    🚀 Upgrade to Premium Now
                </button>
                <div class="payment-methods">
                    <span class="payment-method">GPay</span>
                    <span class="payment-method">UPI</span>
                    <span class="payment-method">Cards</span>
                    <span class="payment-method">NetBanking</span>
                </div>
                <div class="secure">🔒 Secured by Razorpay • Instant activation</div>
                <div class="loading" id="loading">
                    <div class="spinner"></div>
                    <p style="margin-top: 12px; color: #667eea;">Processing payment...</p>
                </div>
            </div>
        </div>
    </div>
    <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
    <script>
        async function initiatePayment() {
            try {
                const response = await fetch('/api/payment/create-order', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                const order = await response.json();
                if (!order.success) {
                    alert('Error: ' + order.message);
                    return;
                }
                const options = {
                    key: '{{ razorpay_key }}',
                    amount: order.amount,
                    currency: order.currency,
                    name: 'Measulor',
                    description: 'Premium Lifetime Access',
                    order_id: order.order_id,
                    handler: function(response) {
                        verifyPayment(response);
                    },
                    prefill: { name: '', email: '', contact: '' },
                    theme: { color: '#667eea' },
                    modal: {
                        ondismiss: function() {
                            console.log('Payment cancelled');
                        }
                    }
                };
                const rzp = new Razorpay(options);
                rzp.open();
            } catch (error) {
                alert('Error initiating payment: ' + error.message);
            }
        }
        async function verifyPayment(payment) {
            document.getElementById('loading').style.display = 'block';
            try {
                const response = await fetch('/api/payment/verify', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payment)
                });
                const result = await response.json();
                if (result.success) {
                    window.location.href = '/payment/success?license=' + result.license_key;
                } else {
                    alert('Payment verification failed: ' + result.message);
                    document.getElementById('loading').style.display = 'none';
                }
            } catch (error) {
                alert('Error: ' + error.message);
                document.getElementById('loading').style.display = 'none';
            }
        }
    </script>
</body>
</html>
'''

SUCCESS_PAGE_HTML = '''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Payment Successful</title><style>*{margin:0;padding:0;box-sizing:border-box;font-family:-apple-system,system-ui,sans-serif}body{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}.card{background:white;border-radius:16px;box-shadow:0 20px 60px rgba(0,0,0,0.3);padding:48px;text-align:center;max-width:500px}.success-icon{font-size:64px;margin-bottom:24px}.title{font-size:28px;font-weight:700;color:#1a202c;margin-bottom:12px}.message{color:#4a5568;font-size:16px;line-height:1.6;margin-bottom:32px}.license-box{background:#f7fafc;border:2px dashed #cbd5e0;border-radius:12px;padding:24px;margin-bottom:32px}.license-label{color:#718096;font-size:14px;font-weight:600;margin-bottom:8px}.license-key{font-size:24px;font-weight:700;color:#667eea;font-family:monospace;word-break:break-all}.btn{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;padding:14px 32px;border:none;border-radius:12px;font-size:16px;font-weight:600;cursor:pointer;text-decoration:none;display:inline-block;margin:8px}.btn:hover{transform:translateY(-2px);box-shadow:0 8px 16px rgba(102,126,234,0.4)}</style></head><body><div class="card"><div class="success-icon">✅</div><h1 class="title">Payment Successful!</h1><p class="message">Thank you for upgrading to Measulor Premium. Your license key has been generated and is ready to use.</p><div class="license-box"><div class="license-label">YOUR LICENSE KEY</div><div class="license-key">{{ license_key }}</div></div><p style="color:#718096;font-size:14px;margin-bottom:24px">Save this license key securely. You'll need it to activate premium features.</p><a href="/" class="btn">🏠 Go to Home</a><a href="mailto:support@measulor.com?subject=License Key: {{ license_key }}" class="btn" style="background:#48bb78">📧 Email License</a></div></body></html>
'''

# Flask Routes
@payment_bp.route('/payment')
def payment_page():
    """Render the payment page"""
    return render_template_string(PAYMENT_PAGE_HTML, razorpay_key=RAZORPAY_KEY_ID)

@payment_bp.route('/api/payment/create-order', methods=['POST'])
def create_order():
    """Create a Razorpay order"""
    try:
        if not razorpay_client:
            return jsonify({
                'success': False,
                'message': 'Razorpay SDK not installed. Run: pip install razorpay'
            }), 500
        
        # Create order
        order_data = {
            'amount': PRODUCT_PRICE,  # Amount in paise
            'currency': 'INR',
            'receipt': f'rcpt_{secrets.token_hex(8)}',
            'notes': {
                'product': PRODUCT_NAME
            }
        }
        
        order = razorpay_client.order.create(data=order_data)
        
        # Store order in database
        orders_db[order['id']] = {
            'order_id': order['id'],
            'amount': PRODUCT_PRICE,
            'currency': 'INR',
            'status': 'created',
            'created_at': datetime.now().isoformat(),
            'license_key': None
        }
        
        return jsonify({
            'success': True,
            'order_id': order['id'],
            'amount': order['amount'],
            'currency': order['currency']
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@payment_bp.route('/api/payment/verify', methods=['POST'])
def verify_payment():
    """Verify Razorpay payment signature"""
    try:
        if not razorpay_client:
            return jsonify({'success': False, 'message': 'Razorpay not configured'}), 500
        
        data = request.json
        razorpay_order_id = data.get('razorpay_order_id')
        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_signature = data.get('razorpay_signature')
        
        # Verify signature
        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }
        
        razorpay_client.utility.verify_payment_signature(params_dict)
        
        # Payment verified - Generate license key
        license_key = generate_license_key()
        
        # Update order
        if razorpay_order_id in orders_db:
            orders_db[razorpay_order_id]['status'] = 'paid'
            orders_db[razorpay_order_id]['payment_id'] = razorpay_payment_id
            orders_db[razorpay_order_id]['license_key'] = license_key
            orders_db[razorpay_order_id]['paid_at'] = datetime.now().isoformat()
        
        # Store license
        licenses_db[license_key] = {
            'order_id': razorpay_order_id,
            'payment_id': razorpay_payment_id,
            'status': 'active',
            'created_at': datetime.now().isoformat()
        }
        
        # Save to file for persistence
        try:
            with open('licenses.json', 'w') as f:
                json.dump(licenses_db, f, indent=2)
        except:
            pass
        
        return jsonify({
            'success': True,
            'license_key': license_key,
            'message': 'Payment verified successfully'
        })
    
    except razorpay.errors.SignatureVerificationError:
        return jsonify({
            'success': False,
            'message': 'Invalid payment signature'
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@payment_bp.route('/payment/success')
def payment_success():
    """Success page after payment"""
    license_key = request.args.get('license', 'N/A')
    return render_template_string(SUCCESS_PAGE_HTML, license_key=license_key)

@payment_bp.route('/api/payment/validate-license', methods=['POST'])
def validate_license():
    """Validate a license key"""
    data = request.json
    license_key = data.get('license_key', '')
    
    if license_key in licenses_db:
        license_info = licenses_db[license_key]
        if license_info['status'] == 'active':
            return jsonify({
                'valid': True,
                'message': 'License is active',
                'created_at': license_info['created_at']
            })
    
    return jsonify({
        'valid': False,
        'message': 'Invalid or expired license key'
    }), 404

@payment_bp.route('/api/payment/webhook', methods=['POST'])
def razorpay_webhook():
    """Handle Razorpay webhooks for payment notifications"""
    try:
        webhook_secret = os.getenv('RAZORPAY_WEBHOOK_SECRET', '')
        webhook_signature = request.headers.get('X-Razorpay-Signature')
        webhook_body = request.get_data()
        
        if webhook_secret:
            # Verify webhook signature
            razorpay_client.utility.verify_webhook_signature(
                webhook_body.decode('utf-8'),
                webhook_signature,
                webhook_secret
            )
        
        event = request.json
        
        # Handle different events
        if event['event'] == 'payment.captured':
            payment = event['payload']['payment']['entity']
            print(f"Payment captured: {payment['id']}")
            # You can send email notifications here
        
        return jsonify({'status': 'ok'})
    
    except Exception as e:
        print(f"Webhook error: {e}")
        return jsonify({'error': str(e)}), 400
