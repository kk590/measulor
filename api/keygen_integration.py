"""Keygen.sh license integration for Measulor."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Tuple

import requests

LOGGER = logging.getLogger(__name__)

KEYGEN_ACCOUNT_ID = os.getenv("KEYGEN_ACCOUNT_ID")
KEYGEN_PRODUCT_ID = os.getenv("KEYGEN_PRODUCT_ID")
KEYGEN_PRODUCT_TOKEN = os.getenv("KEYGEN_PRODUCT_TOKEN")
KEYGEN_API_BASE = os.getenv("KEYGEN_API_URL", "https://api.keygen.sh/v1")
KEYGEN_VALIDATE_TIMEOUT_SECONDS = float(os.getenv("KEYGEN_TIMEOUT_SECONDS", "10"))

# 5 minute in-memory cache for license status.
license_cache: Dict[str, Dict[str, object]] = {}


def get_missing_keygen_env_vars() -> list[str]:
    """Return a list of missing required Keygen env vars."""
    required = {
        "KEYGEN_ACCOUNT_ID": KEYGEN_ACCOUNT_ID,
        "KEYGEN_PRODUCT_ID": KEYGEN_PRODUCT_ID,
        "KEYGEN_PRODUCT_TOKEN": KEYGEN_PRODUCT_TOKEN,
    }
    return [name for name, value in required.items() if not value]


def _build_headers() -> Dict[str, str]:
    return {
        "Content-Type": "application/vnd.api+json",
        "Accept": "application/vnd.api+json",
        "Authorization": f"Bearer {KEYGEN_PRODUCT_TOKEN}",
    }


def verify_license_with_keygen(license_key: str) -> Tuple[bool, Dict[str, object]]:
    """Validate a license key against Keygen."""
    if not license_key:
        return False, {"message": "License key is required"}

    missing_vars = get_missing_keygen_env_vars()
    if missing_vars:
        LOGGER.error("Missing required Keygen env vars: %s", ", ".join(missing_vars))
        return False, {"message": "Keygen credentials are not configured", "missing_vars": missing_vars}

    if license_key in license_cache:
        cached = license_cache[license_key]
        cache_time = cached.get("cached_at", datetime.min)
        if isinstance(cache_time, datetime) and datetime.now() - cache_time < timedelta(minutes=5):
            LOGGER.debug("Returning cached Keygen result for key ending %s", license_key[-6:])
            return bool(cached.get("valid", False)), dict(cached.get("data", {}))

    url = f"{KEYGEN_API_BASE}/accounts/{KEYGEN_ACCOUNT_ID}/licenses/actions/validate-key"
    payload = {
        "meta": {
            "key": license_key,
            "scope": {"product": KEYGEN_PRODUCT_ID},
        }
    }

    try:
        LOGGER.info("Validating Keygen license key ending with %s", license_key[-6:])
        response = requests.post(
            url,
            headers=_build_headers(),
            json=payload,
            timeout=KEYGEN_VALIDATE_TIMEOUT_SECONDS,
        )

        body = response.json() if response.content else {}
        if response.status_code == 200:
            is_valid = bool(body.get("meta", {}).get("valid", False))
            license_cache[license_key] = {
                "valid": is_valid,
                "data": body,
                "cached_at": datetime.now(),
            }
            return is_valid, body

        LOGGER.error(
            "Keygen validation failed: status=%s body=%s",
            response.status_code,
            body,
        )
        return False, {
            "message": "Keygen validation request failed",
            "status_code": response.status_code,
            "response": body,
        }
    except requests.RequestException:
        LOGGER.exception("Network error while validating license with Keygen")
        return False, {"message": "Network error while contacting Keygen"}
    except ValueError:
        LOGGER.exception("Unexpected non-JSON response received from Keygen")
        return False, {"message": "Invalid response from Keygen"}
