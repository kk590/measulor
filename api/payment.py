from flask import Blueprint, render_template_string, request, jsonify
import secrets
import json
from datetime import datetime

payment_bp = Blueprint('payment', __name__)

# Store orders in memory (you can later move this to a database)
orders = {}

PAYMENT_PAGE_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Measulor Premium - Payment</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            min-height: 100vh;
            color: white;
            padding: 20px;
        }
        .container { max-width: 600px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 30px; }
        .header h1 { font-size: 2em; margin-bottom: 10px; }
        .card { 
            background: rgba(255,255,255,0.15);
            border-radius: 15px;
            padding: 30px;
            margin: 20px 0;
            backdrop-filter: blur(10px);
        }
        .price { font-size: 3em; font-weight: 700; text-align: center; margin: 20px 0; }
        .step { 
            background: rgba(255,255,255,0.1);
            border-radius: 10px;
            padding: 15px;
            margin: 15px 0;
            border-left: 4px solid #48bb78;
        }
        .step-number { 
            background: #48bb78;
            color: white;
            width: 30px;
            height: 30px;
            border-radius: 50%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            margin-right: 10px;
        }
        .upi-box {
            background: white;
            color: #333;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            margin: 20px 0;
        }
        .upi-id {
            font-size: 1.3em;
            font-weight: 700;
            color: #667eea;
            padding: 15px;
            background: #f7fafc;
            border-radius: 8px;
            margin: 10px 0;
            word-break: break-all;
        }
        .copy-btn {
            background: #48bb78;
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 8px;
            font-size: 1em;
            font-weight: 600;
            cursor: pointer;
            margin: 10px 5px;
        }
        .copy-btn:hover { background: #38a169; }
        .form-group { margin: 20px 0; }
        .form-group label { 
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
        }
        .form-group input {
            width: 100%;
            padding: 12px;
            border-radius: 8px;
            border: none;
            font-size: 1em;
        }
        .submit-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 15px;
            border-radius: 10px;
            font-size: 1.1em;
            font-weight: 700;
            width: 100%;
            cursor: pointer;
            margin-top: 20px;
        }
        .submit-btn:hover { background: #5568d3; }
        .alert {
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
            display: none;
        }
        .alert-success { background: #48bb78; }
        .alert-error { background: #f56565; }
        .features {
            margin: 20px 0;
        }
        .feature-item {
            padding: 8px 0;
            display: flex;
            align-items: center;
        }
        .feature-item::before {
            content: '✓';
            color: #48bb78;
            font-weight: 700;
            font-size: 1.2em;
            margin-right: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>👕 Measulor Premium</h1>
            <p>Complete Your Payment</p>
        </div>

        <div class="card">
            <div class="price">₹499</div>
            <p style="text-align: center; margin-bottom: 20px;">One-time payment • Lifetime access</p>
            
            <div class="features">
                <div class="feature-item">Real AI-powered measurements (MediaPipe)</div>
                <div class="feature-item">Measure: Shoulders, Chest, Waist, Hips, Arms, Legs</div>
                <div class="feature-item">Save & track measurement history</div>
                <div class="feature-item">Export measurements as CSV/PDF</div>
                <div class="feature-item">Mobile-friendly camera interface</div>
            </div>
        </div>

        <div class="card">
            <h2 style="margin-bottom: 20px;">💳 Payment Instructions</h2>
            
            <div class="step">
                <span class="step-number">1</span>
                <strong>Open GPay/PhonePe/Paytm</strong>
            </div>
            
            <div class="step">
                <span class="step-number">2</span>
                <strong>Send ₹499 to this UPI ID:</strong>
                <div class="upi-box">
                    <div class="upi-id" id="upiId">YOUR-UPI-ID@okaxis</div>
                    <button class="copy-btn" onclick="copyUPI()">📋 Copy UPI ID</button>
                </div>
            </div>
            
            <div class="step">
                <span class="step-number">3</span>
                <strong>Screenshot the payment confirmation</strong>
            </div>
            
            <div class="step">
                <span class="step-number">4</span>
                <strong>Fill the form below & submit</strong>
            </div>
        </div>

        <div class="card">
            <h2 style="margin-bottom: 20px;">📝 Order Form</h2>
            <div class="alert alert-success" id="successAlert"></div>
            <div class="alert alert-error" id="errorAlert"></div>
            
            <form id="orderForm" onsubmit="submitOrder(event)">
                <div class="form-group">
                    <label>Your Email</label>
                    <input type="email" id="email" required placeholder="your@email.com">
                </div>
                
                <div class="form-group">
                    <label>Your Name</label>
                    <input type="text" id="name" required placeholder="Full Name">
                </div>
                
                <div class="form-group">
                    <label>UPI Transaction ID</label>
                    <input type="text" id="transactionId" required placeholder="e.g., 123456789012">
                    <small style="opacity: 0.8;">Find this in your payment app</small>
                </div>
                
                <button type="submit" class="submit-btn">🚀 Submit Order</button>
            </form>
            
            <p style="text-align: center; margin-top: 20px; font-size: 0.9em; opacity: 0.8;">
                We'll verify your payment and send your license key to your email within 2-4 hours.
            </p>
        </div>
    </div>

    <script>
        function copyUPI() {
            const upiId = document.getElementById('upiId').textContent;
            navigator.clipboard.writeText(upiId);
            alert('UPI ID copied! ✓');
        }

        async function submitOrder(e) {
            e.preventDefault();
            
            const email = document.getElementById('email').value;
            const name = document.getElementById('name').value;
            const transactionId = document.getElementById('transactionId').value;
            
            const successAlert = document.getElementById('successAlert');
            const errorAlert = document.getElementById('errorAlert');
            successAlert.style.display = 'none';
            errorAlert.style.display = 'none';
            
            try {
                const response = await fetch('/api/payment/submit', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, name, transaction_id: transactionId })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    successAlert.textContent = '✅ Order submitted successfully! Check your email for license key (2-4 hours).';
                    successAlert.style.display = 'block';
                    document.getElementById('orderForm').reset();
                } else {
                    errorAlert.textContent = '❌ ' + data.message;
                    errorAlert.style.display = 'block';
                }
            } catch (error) {
                errorAlert.textContent = '❌ Error submitting order. Please try again.';
                errorAlert.style.display = 'block';
            }
        }
    </script>
</body>
</html>
'''

@payment_bp.route('/payment')
def payment_page():
    return render_template_string(PAYMENT_PAGE_HTML)

@payment_bp.route('/api/payment/submit', methods=['POST'])
def submit_payment():
    try:
        data = request.json
        email = data.get('email')
        name = data.get('name')
        transaction_id = data.get('transaction_id')
        
        if not email or not name or not transaction_id:
            return jsonify({'success': False, 'message': 'All fields are required'}), 400
        
        # Generate order ID
        order_id = 'ORD-' + secrets.token_hex(8).upper()
        
        # Store order
        orders[order_id] = {
            'email': email,
            'name': name,
            'transaction_id': transaction_id,
            'amount': 499,
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'license_key': None
        }
        
        # Save to file (for persistence)
        try:
            with open('orders.json', 'w') as f:
                json.dump(orders, f, indent=2)
        except:
            pass
        
        return jsonify({
            'success': True,
            'order_id': order_id,
            'message': 'Order received! We will verify and send license key to your email.'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@payment_bp.route('/api/payment/orders')
def get_orders():
    """Admin endpoint to view all orders"""
    return jsonify({'orders': orders})
