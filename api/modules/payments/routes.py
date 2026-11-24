"""HTTP endpoints for Paddle checkout, purchase claiming, customer portal and webhooks."""

import json
import logging
import re

from flask import Blueprint, current_app, jsonify, request, session

from .paddle import PaddleError, verify_signature

logger = logging.getLogger(__name__)
bp = Blueprint("payments", __name__, url_prefix="/api/payments")

TRANSACTION_ID = re.compile(r"^txn_[a-z0-9]{26}$")


def _services():
    ext = current_app.extensions["measulor"]
    return ext["config"], ext["entitlements"], ext["paddle"]


@bp.get("/config")
def payment_config():
    config, store, _ = _services()
    return jsonify({
        "required": config.require_payment,
        "environment": config.paddle_environment,
        "client_token": config.paddle_client_token,
        "price_id": config.paddle_price_id,
        "checkout_url": config.paddle_checkout_url,
        "price_label": config.price_label,
        "entitlement": store.summary(session.get("customer_id")),
    })


@bp.post("/claim")
def claim_transaction():
    """Link a completed checkout to this browser session after verifying it with Paddle."""
    config, store, paddle = _services()
    if paddle is None:
        return jsonify({"success": False, "message": "Payments are not configured"}), 503
    transaction_id = (request.get_json(silent=True) or {}).get("transaction_id", "").strip()
    if not TRANSACTION_ID.match(transaction_id):
        return jsonify({"success": False, "message": "Invalid transaction ID"}), 400
    try:
        transaction = paddle.get_transaction(transaction_id)
    except PaddleError as exc:
        logger.warning("Claim of %s failed: %s", transaction_id, exc)
        return jsonify({"success": False, "message": "Transaction not found"}), 404

    if transaction.get("status") not in ("paid", "completed"):
        return jsonify({"success": False, "pending": True,
                        "message": "Payment is still processing. Try again in a few seconds."}), 409
    customer_id = store.record_transaction(transaction)
    if not customer_id:
        return jsonify({"success": False, "message": "Transaction does not include this product"}), 400
    session["customer_id"] = customer_id
    session.permanent = True
    return jsonify({"success": True, "entitlement": store.summary(customer_id)})


@bp.post("/portal")
def customer_portal():
    _, store, paddle = _services()
    customer_id = session.get("customer_id")
    if paddle is None or not customer_id:
        return jsonify({"success": False, "message": "No purchase linked to this browser"}), 400
    try:
        portal = paddle.create_portal_session(customer_id, store.active_subscription_ids(customer_id))
    except PaddleError as exc:
        logger.error("Portal session failed: %s", exc)
        return jsonify({"success": False, "message": "Could not open billing portal"}), 502
    return jsonify({"success": True, "url": portal.get("urls", {}).get("general", {}).get("overview")})


@bp.post("/logout")
def unlink():
    session.pop("customer_id", None)
    return jsonify({"success": True})


@bp.post("/webhook")
def webhook():
    config, store, _ = _services()
    raw = request.get_data(cache=False)
    if not verify_signature(raw, request.headers.get("Paddle-Signature", ""),
                            config.paddle_webhook_secret, config.paddle_webhook_tolerance_seconds):
        return jsonify({"success": False, "message": "Invalid signature"}), 401
    try:
        payload = json.loads(raw)
    except ValueError:
        return jsonify({"success": False, "message": "Invalid JSON"}), 400

    event_id = payload.get("event_id")
    event_type = payload.get("event_type", "")
    data = payload.get("data") or {}
    if not event_id:
        return jsonify({"success": False, "message": "Missing event_id"}), 400
    if not store.mark_event_processed(event_id, event_type):
        return jsonify({"success": True, "duplicate": True})

    try:
        if event_type in ("transaction.paid", "transaction.completed"):
            store.record_transaction(data)
        elif event_type.startswith("subscription."):
            store.record_subscription(data)
        elif event_type in ("adjustment.created", "adjustment.updated"):
            store.record_refund(data)
    except Exception:
        store.unmark_event(event_id)  # let Paddle retry
        logger.exception("Failed to process webhook %s (%s)", event_id, event_type)
        return jsonify({"success": False}), 500

    logger.info("Processed Paddle webhook %s (%s)", event_id, event_type)
    return jsonify({"success": True})
