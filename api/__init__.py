"""Measulor: video -> 3D model -> body measurements, monetised with Paddle."""

import logging
import os
from datetime import timedelta
from typing import Optional

from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

from .config import Config
from .db import make_engine
from .jobs import JobService
from .modules.payments import EntitlementStore, PaddleClient
from .modules.payments import bp as payments_bp
from .pipeline import run as run_pipeline
from .routes import bp as main_bp

CONTENT_SECURITY_POLICY = "; ".join([
    "default-src 'self'",
    "script-src 'self' https://cdn.paddle.com https://sandbox-cdn.paddle.com https://public.profitwell.com",
    "style-src 'self' 'unsafe-inline' https://cdn.paddle.com https://sandbox-cdn.paddle.com",
    "img-src 'self' data: https:",
    "connect-src 'self' https://*.paddle.com https://www2.profitwell.com",
    "frame-src https://*.paddle.com",
    "frame-ancestors 'none'",
])


def create_app(config: Optional[Config] = None, runner=run_pipeline) -> Flask:
    config = (config or Config()).finalize()
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    app = Flask(__name__)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    app.config.update(
        SECRET_KEY=config.secret_key,
        MAX_CONTENT_LENGTH=config.max_upload_mb * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=config.is_production,
        PERMANENT_SESSION_LIFETIME=timedelta(days=365),
    )
    if config.cors_origins:
        CORS(app, origins=config.cors_origins, supports_credentials=True)

    engine = make_engine(config.database_url)
    entitlements = EntitlementStore(engine, config.paddle_price_id, config.scans_per_purchase)
    paddle = PaddleClient(config.paddle_api_base, config.paddle_api_key) if config.paddle_api_key else None
    app.extensions["measulor"] = {
        "config": config,
        "engine": engine,
        "entitlements": entitlements,
        "paddle": paddle,
        "jobs": JobService(engine, config, entitlements, runner),
    }

    app.register_blueprint(main_bp)
    app.register_blueprint(payments_bp)

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        if config.is_production:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response

    @app.errorhandler(413)
    def too_large(_):
        return jsonify({"success": False, "message": f"File too large. Maximum is {config.max_upload_mb} MB"}), 413

    @app.errorhandler(404)
    def not_found(_):
        return jsonify({"success": False, "message": "Not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(_):
        return jsonify({"success": False, "message": "Method not allowed"}), 405

    @app.errorhandler(500)
    def server_error(_):
        return jsonify({"success": False, "message": "Internal server error"}), 500

    return app
