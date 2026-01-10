# Hybrid Payment System for Measulor
# Instamojo (Auto) + Manual UPI (Backup) - No PAN Required!

from flask import Blueprint, render_template_string, request, jsonify, redirect
import os
import secrets
import json
from datetime import datetime
import requests

payment_bp = Blueprint('payment', __name__)

# Instamojo Configuration (No PAN needed initially!)
# Sign up: https://www.instamojo.com/
INSTAMOJO_API_KEY = os.getenv('INSTAMOJO_API_KEY', 'test_YOUR_API_KEY')
INSTAMOJO_AUTH_TOKEN = os.getenv('INSTAMOJO_AUTH_TOKEN', 'test_YOUR_AUTH_TOKEN')
INSTAMOJO_ENDPOINT = 'https://test.instamojo.com/api/1.1/'  # Use 'https://www.instamojo.com/api/1.1/' for live

# Your UPI ID for manual payments (FREE - 0% fees)
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
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Measulor Premium Payment</title><style>*{margin:0;padding:0;box-sizing:border-box;font-family:-apple-system,sans-serif}body{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);min-height:100vh;padding:20px}.container{max-width:600px;margin:0 auto}.header{text-align:center;color:white;margin-bottom:30px}.header h1{font-size:32px;margin-bottom:10px}.card{background:white;border-radius:16px;padding:30px;margin:20px 0;box-shadow:0 20px 60px rgba(0,0,0,0.3)}.price{text-align:center;margin-bottom:30px}.price-amount{font-size:48px;font-weight:700;color:#1a202c}.price-period{color:#718096;margin-top:5px}.features{margin:20px 0}.feature{padding:12px 0;border-bottom:1px solid #e2e8f0;display:flex;align-items:center}.feature:last-child{border:none}.feature-icon{color:#48bb78;margin-right:10px;font-size:18px}.payment-options{display:grid;gap:15px;margin-top:30px}.payment-btn{padding:18px;border:2px solid #e2e8f0;border-radius:12px;background:white;cursor:pointer;transition:all .3s;text-align:left}.payment-btn:hover{border-color:#667eea;transform:translateY(-2px);box-shadow:0 8px 16px rgba(102,126,234,0.2)}.payment-btn.recommended{border-color:#48bb78;background:#f0fdf4}.recommended-badge{background:#48bb78;color:white;padding:4px 12px;border-radius:12px;font-size:12px;font-weight:600;display:inline-block;margin-bottom:8px}.btn-title{font-size:18px;font-weight:700;color:#1a202c;margin:8px 0}.btn-desc{color:#718096;font-size:14px;margin:5px 0}.btn-fee{color:#48bb78;font-weight:600;font-size:13px}.modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.8);z-index:1000;align-items:center;justify-content:center}.modal.active{display:flex}.modal-content{background:white;border-radius:16px;padding:30px;max-width:500px;width:90%;max-height:80vh;overflow-y:auto}.modal-close{float:right;font-size:28px;cursor:pointer;color:#718096}.upi-box{background:#f7fafc;padding:20px;border-radius:12px;text-align:center;margin:20px 0}.upi-id{font-size:20px;font-weight:700;color:#667eea;padding:15px;background:white;border-radius:8px;word-break:break-all;margin:10px 0}.copy-btn,.submit-btn{background:#667eea;color:white;border:none;padding:14px 24px;border-radius:8px;font-weight:600;cursor:pointer;width:100%;margin:8px 0}.copy-btn:hover,.submit-btn:hover{background:#5568d3}input[type=email],input[type=text]{width:100%;padding:12px;border:2px solid #e2e8f0;border-radius:8px;margin:10px 0;font-size:15px}input:focus{border-color:#667eea;outline:none}.form-group{margin:15px 0}.form-group label{display:block;margin-bottom:8px;font-weight:600;color:#4a5568}.alert{padding:15px;border-radius:8px;margin:15px 0;display:none}.alert-success{background:#48bb78;color:white}.alert-error{background:#f56565;color:white}</style></head><body><div class="container"><div class="header"><h1>👕 Measulor Premium</h1><p>Choose your payment method</p></div><div class="card"><div class="price"><div class="price-amount">₹499</div><div class="price-period">One-time • Lifetime access</div></div><div class="features"><div class="feature"><span class="feature-icon">✓</span>AI-powered body measurements</div><div class="feature"><span class="feature-icon">✓</span>All body parts measurement</div><div class="feature"><span class="feature-icon">✓</span>Save & export reports</div><div class="feature"><span class="feature-icon">✓</span>Lifetime updates</div></div><div class="payment-options"><div class="payment-btn recommended" onclick="payInstamojo()"><span class="recommended-badge">RECOMMENDED</span><div class="btn-title">💳 Automatic Payment</div><div class="btn-desc">GPay, UPI, Cards, NetBanking</div><div class="btn-fee">Fee: ₹13 (2% + ₹3) • Instant activation</div></div><div class="payment-btn" onclick="showManualUPI()"><div class="btn-title">📱 Manual UPI Payment</div><div class="btn-desc">Pay via GPay/PhonePe/Paytm</div><div class="btn-fee">Fee: FREE (₹0) • Manual verification (2-4 hours)</div></div></div></div></div><div class="modal" id="upiModal"><div class="modal-content"><span class="modal-close" onclick="closeModal()">&times;</span><h2 style="margin-bottom:20px">📱 Manual UPI Payment</h2><p style="color:#718096;margin-bottom:20px">Send ₹499 to the UPI ID below using any UPI app</p><div class="upi-box"><div style="color:#718096;font-size:14px;margin-bottom:10px">Send Payment To:</div><div class="upi-id" id="upiIdDisplay">{{ upi_id }}</div><button class="copy-btn" onclick="copyUPI()">📋 Copy UPI ID</button></div><form onsubmit="submitManualPayment(event)"><div class="alert alert-success" id="successAlert"></div><div class="alert alert-error" id="errorAlert"></div><div class="form-group"><label>Your Email</label><input type="email" id="email" required placeholder="your@email.com"></div><div class="form-group"><label>Your Name</label><input type="text" id="name" required placeholder="Full Name"></div><div class="form-group"><label>UPI Transaction ID</label><input type="text" id="transactionId" required placeholder="e.g., 123456789012"><small style="color:#718096">Find in your UPI app payment history</small></div><button type="submit" class="submit-btn">✅ Submit Payment Proof</button></form></div></div><script>function payInstamojo(){fetch('/api/payment/instamojo',{method:'POST',headers:{'Content-Type':'application/json'}}).then(r=>r.json()).then(data=>{if(data.success){window.location.href=data.payment_url}else{alert('Error: '+data.message)}}).catch(e=>alert('Error: '+e.message))}function showManualUPI(){document.getElementById('upiModal').classList.add('active')}function closeModal(){document.getElementById('upiModal').classList.remove('active')}function copyUPI(){const upiId=document.getElementById('upiIdDisplay').textContent;navigator.clipboard.writeText(upiId);alert('UPI ID copied! ✓')}function submitManualPayment(e){e.preventDefault();const email=document.getElementById('email').value;const name=document.getElementById('name').value;const transactionId=document.getElementById('transactionId').value;fetch('/api/payment/manual',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,name,transaction_id:transactionId})}).then(r=>r.json()).then(data=>{if(data.success){document.getElementById('successAlert').textContent='✅ Payment proof submitted! Check email in 2-4 hours.';document.getElementById('successAlert').style.display='block';document.getElementById('errorAlert').style.display='none'}else{document.getElementById('errorAlert').textContent='❌ '+data.message;document.getElementById('errorAlert').style.display='block'}}).catch(e=>{document.getElementById('errorAlert').textContent='❌ Error submitting';document.getElementById('errorAlert').style.display='block'})}</script></body></html>
'''

# Flask Routes
@payment_bp.route('/payment')
def payment_page():
    return render_template_string(PAYMENT_PAGE_HTML, upi_id=YOUR_UPI_ID)

@payment_bp.route('/api/payment/instamojo', methods=['POST'])
def instamojo_payment():
    """Create Instamojo payment link - Auto payment (GPay/UPI/Cards)"""
    try:
        headers = {
            'X-Api-Key': INSTAMOJO_API_KEY,
            'X-Auth-Token': INSTAMOJO_AUTH_TOKEN
        }
        
        payload = {
            'purpose': PRODUCT_NAME,
            'amount': PRODUCT_PRICE,
            'buyer_name': '',
            'email': '',
            'redirect_url': request.host_url + 'payment/success',
            'webhook': request.host_url + 'api/payment/instamojo-webhook',
            'send_email': False,
            'send_sms': False,
            'allow_repeated_payments': True
        }
        
        response = requests.post(
            INSTAMOJO_ENDPOINT + 'payment-requests/',
            data=payload,
            headers=headers
        )
        
        data = response.json()
        
        if data.get('success'):
            payment_request = data['payment_request']
            
            # Store order
            order_id = payment_request['id']
            orders_db[order_id] = {
                'order_id': order_id,
                'amount': PRODUCT_PRICE,
                'type': 'instamojo',
                'status': 'created',
                'created_at': datetime.now().isoformat()
            }
            
            return jsonify({
                'success': True,
                'payment_url': payment_request['longurl']
            })
        else:
            return jsonify({
                'success': False,
                'message': data.get('message', 'Instamojo error')
            }), 400
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

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
        <html><head><meta charset="UTF-8"><title>Payment Successful</title><style>*{margin:0;padding:0;box-sizing:border-box;font-family:-apple-system,sans-serif}body{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}.card{background:white;border-radius:16px;padding:48px;text-align:center;max-width:500px;box-shadow:0 20px 60px rgba(0,0,0,0.3)}.success-icon{font-size:64px;margin-bottom:24px}.title{font-size:28px;font-weight:700;color:#1a202c;margin-bottom:12px}.message{color:#4a5568;font-size:16px;margin-bottom:32px}.license-box{background:#f7fafc;border:2px dashed #cbd5e0;border-radius:12px;padding:24px;margin-bottom:32px}.license-label{color:#718096;font-size:14px;font-weight:600;margin-bottom:8px}.license-key{font-size:24px;font-weight:700;color:#667eea;font-family:monospace;word-break:break-all}.btn{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;padding:14px 32px;border:none;border-radius:12px;font-size:16px;font-weight:600;text-decoration:none;display:inline-block;margin:8px}.btn:hover{transform:translateY(-2px);box-shadow:0 8px 16px rgba(102,126,234,0.4)}</style></head><body><div class="card"><div class="success-icon">✅</div><h1 class="title">Payment Successful!</h1><p class="message">Your license key has been generated successfully.</p><div class="license-box"><div class="license-label">YOUR LICENSE KEY</div><div class="license-key">{{ license_key }}</div></div><p style="color:#718096;font-size:14px;margin-bottom:24px">Check your email for the license key and activation instructions.</p><a href="/" class="btn">🏠 Go to Home</a></div></body></html>
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
