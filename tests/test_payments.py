import time

import pytest

from api.modules.payments import verify_signature
from tests.conftest import PRICE_ID, WEBHOOK_SECRET, send_webhook, sign, transaction

TXN = "txn_" + "a" * 26
CUSTOMER = "ctm_01testcustomer00000000000"


def test_signature_valid_and_rotated_secret():
    body = b'{"x":1}'
    header = sign(body)
    assert verify_signature(body, header, WEBHOOK_SECRET, 5)
    rotated = header + ";h1=deadbeef"
    assert verify_signature(body, rotated, WEBHOOK_SECRET, 5)


def test_signature_rejects_tampering_and_replay():
    body = b'{"x":1}'
    assert not verify_signature(b'{"x":2}', sign(body), WEBHOOK_SECRET, 5)
    assert not verify_signature(body, sign(body, secret="other"), WEBHOOK_SECRET, 5)
    assert not verify_signature(body, sign(body, ts=int(time.time()) - 60), WEBHOOK_SECRET, 5)
    assert not verify_signature(body, "garbage", WEBHOOK_SECRET, 5)
    assert not verify_signature(body, "", WEBHOOK_SECRET, 5)


def test_webhook_rejects_bad_signature(client):
    response = client.post("/api/payments/webhook", data=b"{}", headers={"Paddle-Signature": "ts=1;h1=00"})
    assert response.status_code == 401


def test_webhook_grants_credit_once(app, client):
    store = app.extensions["measulor"]["entitlements"]
    assert send_webhook(client, "evt_1", "transaction.completed", transaction(TXN)).status_code == 200
    assert store.balance(CUSTOMER) == 1
    duplicate = send_webhook(client, "evt_1", "transaction.completed", transaction(TXN))
    assert duplicate.get_json()["duplicate"] is True
    send_webhook(client, "evt_2", "transaction.paid", transaction(TXN))
    assert store.balance(CUSTOMER) == 1


def test_webhook_ignores_other_products(app, client):
    store = app.extensions["measulor"]["entitlements"]
    send_webhook(client, "evt_1", "transaction.completed", transaction(TXN, price_id="pri_other"))
    assert store.balance(CUSTOMER) == 0


def test_refund_removes_credit(app, client):
    store = app.extensions["measulor"]["entitlements"]
    send_webhook(client, "evt_1", "transaction.completed", transaction(TXN))
    send_webhook(client, "evt_2", "adjustment.updated",
                 {"action": "refund", "status": "approved", "transaction_id": TXN})
    assert store.balance(CUSTOMER) == 0


def test_subscription_lifecycle(app, client):
    store = app.extensions["measulor"]["entitlements"]
    sub = {"id": "sub_1", "customer_id": CUSTOMER, "status": "active", "items": [{"price": {"id": PRICE_ID}}]}
    send_webhook(client, "evt_1", "subscription.created", sub)
    assert store.summary(CUSTOMER)["subscription_active"]
    send_webhook(client, "evt_2", "subscription.canceled", {**sub, "status": "canceled"})
    assert not store.summary(CUSTOMER)["can_scan"]


def test_subscription_transaction_does_not_grant_credits(app, client):
    store = app.extensions["measulor"]["entitlements"]
    send_webhook(client, "evt_1", "transaction.completed", transaction(TXN, subscription_id="sub_9"))
    summary = store.summary(CUSTOMER)
    assert summary["scans_remaining"] == 0 and summary["subscription_active"]


def test_claim_links_session(app, client):
    paddle = app.extensions["measulor"]["paddle"]
    paddle.transactions[TXN] = transaction(TXN)
    response = client.post("/api/payments/claim", json={"transaction_id": TXN})
    assert response.status_code == 200
    assert response.get_json()["entitlement"]["scans_remaining"] == 1
    config = client.get("/api/payments/config").get_json()
    assert config["required"] and config["entitlement"]["can_scan"]
    # Claiming again (or webhook arriving later) must not double-credit.
    client.post("/api/payments/claim", json={"transaction_id": TXN})
    send_webhook(client, "evt_1", "transaction.completed", transaction(TXN))
    assert app.extensions["measulor"]["entitlements"].balance(CUSTOMER) == 1


def test_claim_pending_and_invalid(app, client):
    paddle = app.extensions["measulor"]["paddle"]
    paddle.transactions[TXN] = transaction(TXN, status="ready")
    assert client.post("/api/payments/claim", json={"transaction_id": TXN}).status_code == 409
    assert client.post("/api/payments/claim", json={"transaction_id": "bad"}).status_code == 400
    missing = "txn_" + "b" * 26
    assert client.post("/api/payments/claim", json={"transaction_id": missing}).status_code == 404


def test_portal_requires_purchase(app, client):
    assert client.post("/api/payments/portal").status_code == 400
    app.extensions["measulor"]["paddle"].transactions[TXN] = transaction(TXN)
    client.post("/api/payments/claim", json={"transaction_id": TXN})
    response = client.post("/api/payments/portal")
    assert response.get_json()["url"].endswith(CUSTOMER)


def test_config_exposes_checkout_link_and_price(make_app):
    app = make_app(paddle_checkout_url="https://pay.paddle.io/checkout/hsc_test", price_label="₹199/month")
    config = app.test_client().get("/api/payments/config").get_json()
    assert config["checkout_url"] == "https://pay.paddle.io/checkout/hsc_test"
    assert config["price_label"] == "₹199/month"


def test_production_accepts_checkout_link_without_client_token(tmp_path):
    from api.config import Config
    config = Config()
    config.env = "production"
    config.data_dir = str(tmp_path)
    config.secret_key = "s"
    config.paddle_api_key = "k"
    config.paddle_price_id = "pri_x"
    config.paddle_webhook_secret = "w"
    config.paddle_client_token = ""
    config.paddle_checkout_url = "https://pay.paddle.io/checkout/hsc_test"
    config.payments_required = None
    assert config.finalize().require_payment
    config.paddle_checkout_url = ""
    with pytest.raises(RuntimeError, match="PADDLE_CHECKOUT_URL"):
        config.finalize()


def test_subscription_for_other_product_is_ignored(app, client):
    store = app.extensions["measulor"]["entitlements"]
    other = {"id": "sub_x", "customer_id": CUSTOMER, "status": "active", "items": [{"price": {"id": "pri_other"}}]}
    send_webhook(client, "evt_1", "subscription.created", other)
    assert not store.summary(CUSTOMER)["subscription_active"]


def test_out_of_order_subscription_events(app, client):
    store = app.extensions["measulor"]["entitlements"]
    sub = {"id": "sub_1", "customer_id": CUSTOMER, "items": [{"price": {"id": PRICE_ID}}]}
    send_webhook(client, "evt_2", "subscription.canceled",
                 {**sub, "status": "canceled", "updated_at": "2026-01-02T00:00:00Z"})
    send_webhook(client, "evt_1", "subscription.updated",
                 {**sub, "status": "active", "updated_at": "2026-01-01T00:00:00Z"})
    assert not store.summary(CUSTOMER)["subscription_active"]


def test_recurring_checkout_waits_for_subscription(app, client):
    store = app.extensions["measulor"]["entitlements"]
    paddle = app.extensions["measulor"]["paddle"]
    paid = transaction(TXN, status="paid", billing_cycle={"interval": "month", "frequency": 1})
    send_webhook(client, "evt_1", "transaction.paid", paid)
    paddle.transactions[TXN] = paid
    assert client.post("/api/payments/claim", json={"transaction_id": TXN}).status_code == 409
    assert store.balance(CUSTOMER) == 0
    completed = {**paid, "status": "completed", "subscription_id": "sub_9"}
    send_webhook(client, "evt_2", "transaction.completed", completed)
    paddle.transactions[TXN] = completed
    assert client.post("/api/payments/claim", json={"transaction_id": TXN}).status_code == 200
    summary = store.summary(CUSTOMER)
    assert summary["subscription_active"] and summary["scans_remaining"] == 0


def test_old_receipt_requires_matching_email(app, client):
    paddle = app.extensions["measulor"]["paddle"]
    paddle.transactions[TXN] = transaction(TXN, billed_at="2026-01-01T00:00:00Z")
    response = client.post("/api/payments/claim", json={"transaction_id": TXN})
    assert response.status_code == 403 and response.get_json()["email_required"]
    assert client.post("/api/payments/claim",
                       json={"transaction_id": TXN, "email": "someone@else.com"}).status_code == 403
    assert client.post("/api/payments/claim",
                       json={"transaction_id": TXN, "email": "Buyer@Example.com"}).status_code == 200


def test_chargeback_revokes_credit(app, client):
    store = app.extensions["measulor"]["entitlements"]
    send_webhook(client, "evt_1", "transaction.completed", transaction(TXN))
    send_webhook(client, "evt_2", "adjustment.created",
                 {"id": "adj_1", "action": "chargeback", "status": "approved", "transaction_id": TXN})
    assert store.balance(CUSTOMER) == 0


def test_chargeback_reversal_restores_credit(app, client):
    store = app.extensions["measulor"]["entitlements"]
    send_webhook(client, "evt_1", "transaction.completed", transaction(TXN))
    send_webhook(client, "evt_2", "adjustment.created",
                 {"id": "adj_1", "action": "chargeback", "status": "approved", "transaction_id": TXN})
    send_webhook(client, "evt_3", "adjustment.created",
                 {"id": "adj_2", "action": "chargeback_reverse", "status": "approved", "transaction_id": TXN})
    assert store.balance(CUSTOMER) == 1


def test_cancellation_blocks_restoring_old_receipt(app, client):
    store = app.extensions["measulor"]["entitlements"]
    send_webhook(client, "evt_1", "subscription.canceled",
                 {"id": "sub_1", "customer_id": CUSTOMER, "status": "canceled", "items": []})
    store.record_transaction(transaction(TXN, subscription_id="sub_1"))
    assert not store.summary(CUSTOMER)["subscription_active"]
