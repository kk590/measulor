from api.pipeline import PipelineError
from tests.conftest import transaction, video_upload, wait_for_job

TXN = "txn_" + "c" * 26
CUSTOMER = "ctm_01testcustomer00000000000"


def buy(app, client):
    app.extensions["measulor"]["paddle"].transactions[TXN] = transaction(TXN)
    assert client.post("/api/payments/claim", json={"transaction_id": TXN}).status_code == 200


def test_health(client):
    assert client.get("/health").get_json() == {"status": "ok"}


def test_index_page_has_no_license_ui(client):
    html = client.get("/").get_data(as_text=True)
    assert "paddle.js" in html
    assert "license" not in html.lower()


def test_job_requires_payment(client):
    response = client.post("/api/jobs", data={"video": video_upload(), "height_cm": "170"})
    assert response.status_code == 402
    assert response.get_json()["payment_required"]


def test_job_validation(app, client):
    buy(app, client)
    assert client.post("/api/jobs", data={"video": video_upload(), "height_cm": "20"}).status_code == 400
    assert client.post("/api/jobs", data={"height_cm": "170"}).status_code == 400
    bad = client.post("/api/jobs", data={"video": video_upload("clip.exe"), "height_cm": "170"})
    assert bad.status_code == 400
    assert app.extensions["measulor"]["entitlements"].balance(CUSTOMER) == 1  # refunded


def test_paid_job_runs_and_consumes_credit(app, client):
    buy(app, client)
    response = client.post("/api/jobs", data={"video": video_upload(), "height_cm": "172"})
    assert response.status_code == 202
    job = wait_for_job(client, response.get_json()["job_id"])
    assert job["status"] == "completed"
    assert job["result"]["measurements"]["height"]["value_cm"] == 172
    assert app.extensions["measulor"]["entitlements"].balance(CUSTOMER) == 0
    again = client.post("/api/jobs", data={"video": video_upload(), "height_cm": "172"})
    assert again.status_code == 402


def test_failed_job_refunds_credit(make_app):
    def failing(*args, **kwargs):
        raise PipelineError("Only 3 usable frames found")

    app = make_app(runner=failing)
    client = app.test_client()
    buy(app, client)
    job_id = client.post("/api/jobs", data={"video": video_upload(), "height_cm": "170"}).get_json()["job_id"]
    job = wait_for_job(client, job_id)
    assert job["status"] == "failed" and "usable frames" in job["error"]
    assert app.extensions["measulor"]["entitlements"].balance(CUSTOMER) == 1


def test_jobs_are_private_to_their_owner(app, client):
    buy(app, client)
    job_id = client.post("/api/jobs", data={"video": video_upload(), "height_cm": "170"}).get_json()["job_id"]
    other = app.test_client()
    assert other.get(f"/api/jobs/{job_id}").status_code == 404


def test_payments_can_be_disabled_for_local_dev(make_app):
    client = make_app(payments_required=False).test_client()
    response = client.post("/api/jobs", data={"video": video_upload(), "height_cm": "170"})
    assert response.status_code == 202
    assert wait_for_job(client, response.get_json()["job_id"])["status"] == "completed"
