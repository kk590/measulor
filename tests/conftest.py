import hashlib
import hmac
import io
import json
import time
from datetime import datetime, timezone

import pytest

from api import create_app
from api.config import Config

WEBHOOK_SECRET = "pdl_ntfset_test_secret"
PRICE_ID = "pri_01testpriceid000000000000"


class FakePaddle:
    def __init__(self):
        self.transactions = {}
        self.customers = {}

    def get_customer(self, customer_id):
        return self.customers.get(customer_id, {"id": customer_id, "email": "buyer@example.com"})

    def get_transaction(self, transaction_id):
        from api.modules.payments import PaddleError
        if transaction_id not in self.transactions:
            raise PaddleError("Not found")
        return self.transactions[transaction_id]

    def create_portal_session(self, customer_id, subscription_ids=None):
        return {"urls": {"general": {"overview": f"https://portal.example/{customer_id}"}}}


def fake_runner(video_path, height, work_dir, config, on_stage):
    for stage in ("video", "reconstruction", "measurements"):
        on_stage(stage)
    return {"video": {}, "model": {"points": 1000, "registered_frames": 20, "total_frames": 20},
            "unit": "cm", "confidence": "high", "body_points": 900,
            "measurements": {"height": {"value_cm": height, "method": "reference"}}}


def make_config(tmp_path, **overrides):
    config = Config()
    config.env = "test"
    config.data_dir = str(tmp_path)
    config.database_url = ""
    config.secret_key = "test-secret"
    config.paddle_api_key = "pdl_test_key"
    config.paddle_client_token = "test_client_token"
    config.paddle_price_id = PRICE_ID
    config.paddle_webhook_secret = WEBHOOK_SECRET
    config.payments_required = True
    config.worker_threads = 1
    for key, value in overrides.items():
        setattr(config, key, value)
    return config


@pytest.fixture
def make_app(tmp_path):
    apps = []

    def _make(runner=fake_runner, **overrides):
        app = create_app(make_config(tmp_path, **overrides), runner=runner)
        app.config["TESTING"] = True
        app.extensions["measulor"]["paddle"] = FakePaddle()
        apps.append(app)
        return app

    yield _make
    for app in apps:
        app.extensions["measulor"]["jobs"].shutdown()


@pytest.fixture
def app(make_app):
    return make_app()


@pytest.fixture
def client(app):
    return app.test_client()


def sign(body: bytes, secret: str = WEBHOOK_SECRET, ts: int = None) -> str:
    ts = int(time.time()) if ts is None else ts
    digest = hmac.new(secret.encode(), f"{ts}:".encode() + body, hashlib.sha256).hexdigest()
    return f"ts={ts};h1={digest}"


def send_webhook(client, event_id, event_type, data):
    body = json.dumps({"event_id": event_id, "event_type": event_type, "data": data}).encode()
    return client.post("/api/payments/webhook", data=body, content_type="application/json",
                       headers={"Paddle-Signature": sign(body)})


def transaction(txn_id, customer_id="ctm_01testcustomer00000000000", status="completed",
                subscription_id=None, price_id=PRICE_ID, billed_at=None, billing_cycle=None):
    billed_at = billed_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {"id": txn_id, "customer_id": customer_id, "status": status, "billed_at": billed_at,
            "subscription_id": subscription_id,
            "items": [{"price": {"id": price_id, "billing_cycle": billing_cycle}, "quantity": 1}]}


def video_upload(name="clip.mp4"):
    return (io.BytesIO(b"not-really-a-video"), name)


def wait_for_job(client, job_id, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = client.get(f"/api/jobs/{job_id}").get_json()["job"]
        if job["status"] in ("completed", "failed"):
            return job
        time.sleep(0.05)
    raise AssertionError("job did not finish")
