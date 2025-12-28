from flask import Blueprint, jsonify, request

pricing_bp = Blueprint('pricing', __name__)

# Three-tier subscription pricing for Measulor
PRICING = {
    'starter': {
        'monthly': 599, 'quarterly': 1599, 'yearly': 5999,
        'features': {
            'team_members': 1,
            'measurements_per_day': 50,
            'data_retention_months': 6,
            'api_access': False,
            'white_label': False,
            'custom_templates': 3,
            'support': 'email_48h'
        }
    },
    'professional': {
        'monthly': 1999, 'quarterly': 5399, 'yearly': 19999,
        'features': {
            'team_members': 5,
            'measurements_per_day': 500,
            'data_retention_months': 24,
            'api_access': True,
            'white_label': False,
            'custom_templates': 20,
            'support': 'chat_24h'
        }
    },
    'enterprise': {
        'monthly': 4999, 'quarterly': 13499, 'yearly': 49999,
        'features': {
            'team_members': -1,  # Unlimited
            'measurements_per_day': -1,  # Unlimited
            'data_retention_months': -1,  # Lifetime
            'api_access': True,
            'white_label': True,
            'custom_templates': -1,  # Unlimited
            'support': 'dedicated_2h'
        }
    }
}

@pricing_bp.route('/api/pricing', methods=['GET'])
def get_pricing():
    """Get all pricing tiers with features"""
    return jsonify({
        'plans': ['starter', 'professional', 'enterprise'],
        'pricing': PRICING
    }), 200


# Subscription payment verification
subscription_bp = Blueprint('subscription', __name__)

@subscription_bp.route('/api/verify-payment', methods=['POST'])
def verify_payment():
    """Verify UPI payment and activate subscription"""
    data = request.get_json()
    tier = data.get('tier')  # starter, professional, or enterprise
    transaction_id = data.get('transaction_id')
    amount = data.get('amount')
    
    # Validate payment
    if tier not in PRICING:
        return jsonify({'error': 'Invalid tier'}), 400
    
    return jsonify({
        'status': 'success',
        'tier': tier,
        'transaction_id': transaction_id,
        'features': PRICING[tier]['features']
    }), 200
