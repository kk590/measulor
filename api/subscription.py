from flask import Blueprint, jsonify, request
subscription_bp = Blueprint("subscription", __name__)
@subscription_bp.route("/api/verify-payment", methods=["POST"])
def verify_payment():
    data = request.get_json()
    return jsonify({"status": "success", "tier": data.get("tier")})
