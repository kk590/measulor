from flask import Blueprint, jsonify

pricing_bp = Blueprint('pricing', __name__)

PRICING = {
    'starter': {'monthly': 599, 'quarterly': 1599, 'yearly': 5999},
    'professional': {'monthly': 1999, 'quarterly': 5399, 'yearly': 19999},
    'enterprise': {'monthly': 4999, 'quarterly': 13499, 'yearly': 49999}
}

@pricing_bp.route('/api/pricing', methods=['GET'])
def get_pricing():
    return jsonify({'plans': list(PRICING.keys()), 'pricing': PRICING})
EOF

# Create subscription.py file
cat > subscription.py << 'EOF'
from flask import Blueprint, jsonify, request
subscription_bp = Blueprint('subscription', __name__)

@subscription_bp.route('/api/verify-payment', methods=['POST'])
def verify_payment():
    data = request.get_json()
    return jsonify({'status': 'success', 'tier': data.get('tier')})
EOF
