"""Application configuration loaded from environment variables."""

import os
import secrets
from dataclasses import dataclass, field
from typing import List, Optional


def _bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    value = os.environ.get(name)
    return int(value) if value not in (None, "") else default


def _list(name: str) -> List[str]:
    return [item.strip() for item in os.environ.get(name, "").split(",") if item.strip()]


@dataclass
class Config:
    env: str = field(default_factory=lambda: os.environ.get("APP_ENV", "development"))
    secret_key: str = field(default_factory=lambda: os.environ.get("SECRET_KEY", ""))
    database_url: str = field(default_factory=lambda: os.environ.get("DATABASE_URL", ""))
    data_dir: str = field(default_factory=lambda: os.environ.get("DATA_DIR", os.path.abspath("data")))
    cors_origins: List[str] = field(default_factory=lambda: _list("CORS_ORIGINS"))

    max_upload_mb: int = field(default_factory=lambda: _int("MAX_UPLOAD_MB", 200))
    max_video_seconds: int = field(default_factory=lambda: _int("MAX_VIDEO_SECONDS", 120))
    max_frames: int = field(default_factory=lambda: _int("MAX_FRAMES", 40))
    frame_max_dimension: int = field(default_factory=lambda: _int("FRAME_MAX_DIMENSION", 1600))
    worker_threads: int = field(default_factory=lambda: _int("WORKER_THREADS", 2))
    keep_artifacts_hours: int = field(default_factory=lambda: _int("KEEP_ARTIFACTS_HOURS", 72))

    # Never silently default the Paddle environment when a client token is present.
    paddle_environment: str = field(
        default_factory=lambda: (os.environ.get("PADDLE_ENVIRONMENT") or "").strip()
    )
    paddle_api_key: str = field(default_factory=lambda: os.environ.get("PADDLE_API_KEY", ""))
    paddle_client_token: str = field(default_factory=lambda: os.environ.get("PADDLE_CLIENT_TOKEN", ""))
    paddle_webhook_secret: str = field(default_factory=lambda: os.environ.get("PADDLE_WEBHOOK_SECRET", ""))
    paddle_price_id: str = field(default_factory=lambda: os.environ.get("PADDLE_PRICE_ID", ""))
    paddle_checkout_url: str = field(default_factory=lambda: os.environ.get("PADDLE_CHECKOUT_URL", ""))
    price_label: str = field(default_factory=lambda: os.environ.get("PRICE_LABEL", "\u20b9199/month"))
    paddle_webhook_tolerance_seconds: int = field(
        default_factory=lambda: _int("PADDLE_WEBHOOK_TOLERANCE_SECONDS", 5)
    )
    scans_per_purchase: int = field(default_factory=lambda: _int("SCANS_PER_PURCHASE", 1))
    payments_required: Optional[bool] = field(
        default_factory=lambda: _bool("PAYMENTS_REQUIRED", True) if "PAYMENTS_REQUIRED" in os.environ else None
    )

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    @property
    def paddle_configured(self) -> bool:
        return bool(
            self.paddle_environment
            and self.paddle_api_key
            and self.paddle_price_id
            and (self.paddle_client_token or self.paddle_checkout_url)
        )

    @property
    def require_payment(self) -> bool:
        if self.payments_required is not None:
            return self.payments_required
        return self.paddle_configured

    @property
    def paddle_api_base(self) -> str:
        if self.paddle_environment == "production":
            return "https://api.paddle.com"
        if self.paddle_environment == "sandbox":
            return "https://sandbox-api.paddle.com"
        raise RuntimeError(
            "PADDLE_ENVIRONMENT must be set to 'sandbox' or 'production' "
            "(refusing to guess which Paddle account to use)"
        )

    def finalize(self) -> "Config":
        if not self.database_url:
            self.database_url = "sqlite:///" + os.path.join(self.data_dir, "measulor.db")
        if not self.secret_key:
            if self.is_production:
                raise RuntimeError("SECRET_KEY must be set in production")
            self.secret_key = secrets.token_hex(32)

        # If any client-facing Paddle credential is set, environment must be explicit.
        if self.paddle_client_token or self.paddle_api_key or self.paddle_checkout_url:
            if self.paddle_environment not in ("sandbox", "production"):
                raise RuntimeError(
                    "PADDLE_ENVIRONMENT must be 'sandbox' or 'production' when Paddle credentials are set"
                )
            if self.paddle_environment == "production" and self.paddle_client_token:
                if not self.paddle_client_token.startswith("live_"):
                    raise RuntimeError(
                        "PADDLE_CLIENT_TOKEN must start with 'live_' when PADDLE_ENVIRONMENT=production"
                    )
            if self.paddle_environment == "sandbox" and self.paddle_client_token:
                if not self.paddle_client_token.startswith("test_"):
                    raise RuntimeError(
                        "PADDLE_CLIENT_TOKEN must start with 'test_' when PADDLE_ENVIRONMENT=sandbox"
                    )

        if self.is_production and self.require_payment:
            missing = [
                name for name, value in (
                    ("PADDLE_ENVIRONMENT", self.paddle_environment),
                    ("PADDLE_API_KEY", self.paddle_api_key),
                    ("PADDLE_CLIENT_TOKEN or PADDLE_CHECKOUT_URL",
                     self.paddle_client_token or self.paddle_checkout_url),
                    ("PADDLE_PRICE_ID", self.paddle_price_id),
                    ("PADDLE_WEBHOOK_SECRET", self.paddle_webhook_secret),
                ) if not value
            ]
            if missing:
                raise RuntimeError("Missing Paddle configuration: " + ", ".join(missing))
        os.makedirs(self.data_dir, exist_ok=True)
        return self
