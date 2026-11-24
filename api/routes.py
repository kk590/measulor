"""Web page, health check and pipeline job endpoints."""

import logging
import os
import uuid

from flask import Blueprint, current_app, jsonify, render_template, request, send_file, session

from .modules import video
from .modules.measurements import MAX_HEIGHT_CM, MIN_HEIGHT_CM

logger = logging.getLogger(__name__)
bp = Blueprint("main", __name__)


def _ext():
    return current_app.extensions["measulor"]


def _owner_id() -> str:
    if "owner_id" not in session:
        session["owner_id"] = uuid.uuid4().hex
        session.permanent = True
    return session["owner_id"]


@bp.get("/")
def index():
    _owner_id()
    return render_template("index.html")


@bp.get("/health")
def health():
    from sqlalchemy import text
    try:
        with _ext()["engine"].connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Health check failed")
        return jsonify({"status": "error"}), 503
    return jsonify({"status": "ok"})


@bp.post("/api/jobs")
def create_job():
    ext = _ext()
    config, store, job_service = ext["config"], ext["entitlements"], ext["jobs"]

    try:
        height = float(request.form.get("height_cm", ""))
    except ValueError:
        return jsonify({"success": False, "message": "Your height in cm is required"}), 400
    if not MIN_HEIGHT_CM <= height <= MAX_HEIGHT_CM:
        return jsonify({"success": False,
                        "message": f"Height must be between {MIN_HEIGHT_CM} and {MAX_HEIGHT_CM} cm"}), 400
    upload = request.files.get("video")
    if upload is None or not upload.filename:
        return jsonify({"success": False, "message": "No video file provided"}), 400

    customer_id = session.get("customer_id")
    charge = None
    if config.require_payment:
        if not customer_id:
            return jsonify({"success": False, "payment_required": True,
                            "message": "Purchase a scan to continue"}), 402
        charge = store.consume(customer_id)
        if charge is None:
            return jsonify({"success": False, "payment_required": True,
                            "message": "No scans remaining. Purchase another scan to continue"}), 402

    try:
        video_path = video.save_upload(upload, os.path.join(config.data_dir, "uploads"))
    except video.VideoError as exc:
        if charge == "credit":
            store.refund_credit(customer_id)
        return jsonify({"success": False, "message": str(exc)}), 400

    job_id = job_service.create(_owner_id(), video_path, height, customer_id, charge)
    return jsonify({"success": True, "job_id": job_id, "entitlement": store.summary(customer_id)}), 202


@bp.get("/api/jobs/<job_id>")
def get_job(job_id):
    job = _ext()["jobs"].get(job_id, _owner_id())
    if job is None:
        return jsonify({"success": False, "message": "Job not found"}), 404
    return jsonify({"success": True, "job": job})


@bp.get("/api/jobs/<job_id>/model.ply")
def download_model(job_id):
    job_service = _ext()["jobs"]
    job = job_service.get(job_id, _owner_id())
    if job is None or not job["has_model"]:
        return jsonify({"success": False, "message": "3D model not available"}), 404
    return send_file(job_service.model_path(job_id), mimetype="application/octet-stream",
                     as_attachment=True, download_name=f"measulor-{job_id[:8]}.ply")
