"""HTTP endpoints for Paddle checkout, purchase claiming, customer portal and webhooks."""

import json
import logging
import re
from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, jsonify, request, session

from ...pricing_tiers import all_price_ids, load_tiers
from .paddle import PaddleError, verify_signature

logger = logging.getLogger(__name__)
bp = Blueprint("payments", __name__, url_prefix="/api/payments")

TRANSACTION_ID = re.compile(r"^txn_[a-z0-9]{26}$")
CLAIM_WITHOUT_EMAIL = timedelta(hours=2)


def _is_recent(transaction: dict) -> bool:
    stamp = transaction.get("billed_at") or transaction.get("created_at")
    if not stamp:
        return False
    try:
        when = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return False
    return datetime.now(timezone.utc) - when <= CLAIM_WITHOUT_EMAIL


def _services():
    ext = current_app.extensions["measulor"]
    return ext["config"], ext["entitlements"], ext["paddle"]


def _request_country() -> str | None:
    """Best-effort country from edge headers. Never invent a code for Paddle."""
    for header in (
        "CF-IPCountry",
        "X-Vercel-IP-Country",
        "X-Country-Code",
        "CloudFront-Viewer-Country",
    ):
        raw = (request.headers.get(header) or "").strip().upper()
        if not raw or raw in {"XX", "T1", "OTHERS", "UNKNOWN", "ZZ"}:
            continue
        if len(raw) == 2 and raw.isalpha():
            return raw
    return None


@bp.get("/config")
def payment_config():
    config, store, _ = _services()
    return jsonify({
        "required": config.require_payment,
        "environment": config.paddle_environment or None,
        "client_token": config.paddle_client_token or None,
        "price_id": config.paddle_price_id or None,
        "checkout_url": config.paddle_checkout_url or None,
        "price_label": config.price_label,
        "entitlement": store.summary(session.get("customer_id")),
        "customer_email": session.get("customer_email") or None,
        "country": _request_country(),
    })


@bp.get("/pricing")
def pricing_config():
    """Public payload for the pricing page (no server API key)."""
    config, _, _ = _services()
    if not config.paddle_environment:
        return jsonify({
            "success": False,
            "message": "PADDLE_ENVIRONMENT is not set (must be sandbox or production)",
        }), 503
    if not config.paddle_client_token:
        return jsonify({
            "success": False,
            "message": "PADDLE_CLIENT_TOKEN is not set",
        }), 503

    tiers = [t.to_public() for t in load_tiers()]
    return jsonify({
        "success": True,
        "environment": config.paddle_environment,
        "client_token": config.paddle_client_token,
        "country": _request_country(),
        "customer_email": session.get("customer_email") or None,
        "success_path": "/welcome",
        "tiers": tiers,
        "price_ids": all_price_ids(),
    })


@bp.post("/claim")
def claim_transaction():
    config, store, paddle = _services()
    if paddle is None:
        return jsonify({"success": False, "message": "Payments are not configured"}), 503
    body = request.get_json(silent=True) or {}
    transaction_id = str(body.get("transaction_id", "")).strip()
    email = str(body.get("email", "")).strip().lower()
    if not TRANSACTION_ID.match(transaction_id):
        return jsonify({"success": False, "message": "Invalid transaction ID"}), 400
    try:
        transaction = paddle.get_transaction(transaction_id)
    except PaddleError as exc:
        logger.warning("Claim of %s failed: %s", transaction_id, exc)
        return jsonify({"success": False, "message": "Transaction not found"}), 404

    if transaction.get("status") not in ("paid", "completed") or store.awaiting_subscription(transaction):
        return jsonify({"success": False, "pending": True,
                        "message": "Payment is still processing. Try again in a few seconds."}), 409
    if not store.transaction_has_price(transaction):
        return jsonify({"success": False, "message": "Transaction does not include this product"}), 400
    if not _is_recent(transaction):
        if not email:
            return jsonify({"success": False, "email_required": True,
                            "message": "Enter the email address used at checkout to restore this purchase"}), 403
        try:
            customer = paddle.get_customer(transaction.get("customer_id", ""))
        except PaddleError as exc:
            logger.warning("Customer lookup for %s failed: %s", transaction_id, exc)
            return jsonify({"success": False, "message": "Could not verify this purchase"}), 502
        if (customer.get("email") or "").strip().lower() != email:
            return jsonify({"success": False, "email_required": True,
                            "message": "That email doesn't match this purchase"}), 403
    customer_id = store.record_transaction(transaction)
    if not customer_id:
        return jsonify({"success": False, "message": "Transaction does not include this product"}), 400
    session["customer_id"] = customer_id
    session.permanent = True
    if email:
        session["customer_email"] = email
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
    session.pop("customer_email", None)
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
            store.record_subscription(data, payload.get("occurred_at"))
        elif event_type in ("adjustment.created", "adjustment.updated"):
            store.record_refund(data)
    except Exception:
        store.unmark_event(event_id)
        logger.exception("Failed to process webhook %s (%s)", event_id, event_type)
        return jsonify({"success": False}), 500

    logger.info("Processed Paddle webhook %s (%s)", event_id, event_type)
    return jsonify({"success": True})
