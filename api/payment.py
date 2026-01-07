# Hybrid Payment System for Measulor
# Manual UPI Payment System for Measulor - No PAN Required!
from flask import Blueprint, render_template_string, request, jsonify, redirect
import os
import secrets
import json
from datetime import datetime
payment_bp = Blueprint('payment', __name__)

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

# Payment Page with Manual UPI only
PAYMENT_PAGE_HTML = '''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale-1"><title>Measulor Premium Payment</title><style>*{margin:0;padding:20px;box-sizing:border-box}body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;min-height:100vh;padding:20px;container{max-width:600px;margin:0 auto;header{text-align:center;color:white;margin-bottom:30px}.header h1{font-size:32px;margin-bottom:8px}.card{background:white;border-radius:16px;padding:30px;box-shadow:0 20px 60px rgba(0,0,0,0.3)}.price{text-align:center;margin-bottom:30px}.price-amount{font-size:48px;font-weight:700;color:#1a202c}.price-period{color:#718096;margin-top:8px}.features{margin:20px 0}.feature{padding:12px 0;border-top:solid 1px #e2e8f0}.feature-icon{color:#48bb78;margin-right:10px;font-size:18px}.payment-options{display:grid;gap:16px;margin-top:30px}.payment-btn{padding:20px;border:2px solid #e2e8f0;border-radius:12px;background:white;cursor:pointer;transition:all .3s;text-align:left}.payment-btn:hover{border-color:#667eea;background:#f7fafc;transform:scale(1.02)}.btn-title{font-size:18px;font-weight:700;color:#1a202c;margin:8px 0}.btn-desc{color:#718096;font-size:14px}.btn-fee{color:#48bb78;margin-top:8px;font-size:13px}.modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.8);z-index:1000;align-items:center;justify-content:center}.modal.active{display:flex}.modal-content{background:white;border-radius:16px;padding:30px;max-width:500px;width:90%;max-height:80vh;overflow-y:auto}.modal-close{float:right;font-size:28px;cursor:pointer;color:#718096}.upi-box{background:#f7fafc;padding:20px;border-radius:12px;text-align:center;margin:20px 0}.upi-id{font-size:20px;font-weight:700;color:#667eea;padding:15px;background:white;border-radius:8px;word-break:break-all;margin:10px 0}.copy-btn,.submit-btn{background:#667eea;color:white;border:none;padding:14px 24px;border-radius:8px;font-weight:600;cursor:pointer;width:100%;margin:8px 0}.copy-btn:hover,.submit-btn:hover{background:#5568d3}input[type=email],input[type=text]{width:100%;padding:12px;border:2px solid #e2e8f0;border-radius:8px;margin:10px 0;font-size:15px}input:focus{border-color:#667eea;outline:none}.form-group{margin:15px 0}.form-group label{display:block;margin-bottom:8px;font-weight:600;color:#4a5568}.alert{padding:15px;border-radius:8px;margin:15px 0;display:none}.alert-success{background:#48bb78;color:white}.alert-error{background:#f56565;color:white}</style></head><body><div class="container"><div class="header"><h1>👕 Measulor Premium</h1><p>Choose your payment method</p></div><div class="card"><div class="price"><div class="price-amount">₹499</div><div class="price-period">Monthly Payment • Subscription Needed</div></div><div class="features"><div class="feature"><span class="feature-icon">✓</span>AI-powered body measurements</div><div class="feature"><span class="feature-icon">✓</span>All body parts measurement</div><div class="feature"><span class="feature-icon">✓</span>Save & export reports</div><div class="feature"><span class="feature-icon">✓</span>Lifetime updates</div></div><div class="payment-options"><div class="payment-btn" onclick="showManualUPI()"><div class="btn-title">📱 Manual UPI Payment</div><div class="btn-desc">Pay via GPay/PhonePe/Paytm</div><div class="btn-fee">Fee: FREE (₹0) • Manual verification (2-4 hours)</div></div></div></div></div><div class="modal" id="upiModal"><div class="modal-content"><span class="modal-close" onclick="closeModal()">×</span><h2 style="margin-bottom:20px">📱 Manual UPI Payment</h2><p style="color:#718096;margin-bottom:20px">Send ₹499 to the UPI ID below using any UPI app</p><div class="upi-box"><div style="color:#718096;font-size:14px;margin-bottom:10px">Send Payment To:</div><div class="upi-id" id="upiIdDisplay">{{ upi_id }}</div><button class="copy-btn" onclick="copyUPI()">📋 Copy UPI ID</button></div><form onsubmit="submitManualPayment(event)"><div class="alert alert-success" id="successAlert"></div><div class="alert alert-error" id="errorAlert"></div><div class="form-group"><label>Your Email</label><input type="email" id="email" required placeholder="your@email.com"></div><div class="form-group"><label>Your Name</label><input type="text" id="name" required placeholder="Full Name"></div><div class="form-group"><label>UPI Transaction ID</label><input type="text" id="transactionId" required placeholder="e.g., 123456789012"><small style="color:#718096">Find in your UPI app payment history</small></div><button type="submit" class="submit-btn">✅ Submit Payment Proof</button></form></div></div><script>function showManualUPI(){document.getElementById('upiModal').classList.add('active')}function closeModal(){document.getElementById('upiModal').classList.remove('active')}function copyUPI(){const upiId=document.getElementById('upiIdDisplay').textContent;navigator.clipboard.writeText(upiId).then(()=>alert('UPI ID copied!')).catch(()=>alert('Failed to copy'))}function submitManualPayment(e){e.preventDefault();const data={email:document.getElementById('email').value,name:document.getElementById('name').value,transaction_id:document.getElementById('transactionId').value};fetch('/api/payment/manual',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}).then(r=>r.json()).then(data=>{if(data.success){document.getElementById('successAlert').textContent=data.message;document.getElementById('successAlert').style.display='block';document.getElementById('errorAlert').style.display='none';setTimeout(()=>window.location.href='/',3000)}else{document.getElementById('errorAlert').textContent=data.message;document.getElementById('errorAlert').style.display='block';document.getElementById('successAlert').style.display='none'}}).catch(e=>{document.getElementById('errorAlert').textContent='Error: '+e.message;document.getElementById('errorAlert').style.display='block'})}</script></body></html>
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
            'message': f'Error: {str(e)}'
        }), 500

@payment_bp.route('/api/payment/verify-manual/<order_id>')
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

@payment_bp.route('/payment/success')
def payment_success():
    """Success page after payment"""
    return render_template_string('''
    <!DOCTYPE html>
    <html><head><title>Payment Successful</title></head>
    <body style="font-family:Arial;text-align:center;padding:50px">
    <h1>✅ Payment Successful!</h1>
    <p>Your license key has been sent to your email.</p>
    <a href="/">Return to Home</a>
    </body></html>
    ''')
