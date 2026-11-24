"""Paddle Billing API client and webhook signature verification."""

import hashlib
import hmac
import time
from typing import Optional

import requests


class PaddleError(RuntimeError):
    """Raised when the Paddle API returns an error or cannot be reached."""


class PaddleClient:
    def __init__(self, api_base: str, api_key: str, timeout: float = 10.0):
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _request(self, method: str, path: str, **kwargs) -> dict:
        try:
            response = requests.request(
                method,
                f"{self.api_base}{path}",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                timeout=self.timeout,
                **kwargs,
            )
        except requests.RequestException as exc:
            raise PaddleError(f"Could not reach Paddle: {exc}") from exc
        if response.status_code == 404:
            raise PaddleError("Not found")
        if response.status_code >= 400:
            try:
                detail = response.json().get("error", {}).get("detail", "")
            except ValueError:
                detail = response.text[:200]
            raise PaddleError(f"Paddle API error {response.status_code}: {detail}")
        return response.json().get("data", {})

    def get_transaction(self, transaction_id: str) -> dict:
        return self._request("GET", f"/transactions/{transaction_id}")

    def create_portal_session(self, customer_id: str, subscription_ids: Optional[list] = None) -> dict:
        body = {"subscription_ids": subscription_ids} if subscription_ids else {}
        return self._request("POST", f"/customers/{customer_id}/portal-sessions", json=body)


def verify_signature(raw_body: bytes, header: str, secret: str, tolerance_seconds: int,
                     now: Optional[float] = None) -> bool:
    """Verify a `Paddle-Signature: ts=...;h1=...` header (HMAC-SHA256 of "ts:body").

    Multiple h1 values may be present while a secret is being rotated; any match is accepted.
    """
    if not header or not secret:
        return False
    timestamp = None
    signatures = []
    for part in header.split(";"):
        key, _, value = part.strip().partition("=")
        if key == "ts":
            timestamp = value
        elif key == "h1" and value:
            signatures.append(value)
    if not timestamp or not signatures or not timestamp.isdigit():
        return False
    current = time.time() if now is None else now
    if abs(current - int(timestamp)) > tolerance_seconds:
        return False
    expected = hmac.new(secret.encode(), timestamp.encode() + b":" + raw_body, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, signature) for signature in signatures)
