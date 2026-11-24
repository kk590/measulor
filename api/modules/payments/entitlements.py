"""Purchase records and scan entitlements backed by the database.

One-time purchases add `scans_per_purchase` credits; an active Paddle subscription
grants unlimited scans while it stays active.
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from ...db import credits, purchases, subscriptions, utcnow, webhook_events

logger = logging.getLogger(__name__)

PAID_TRANSACTION_STATUSES = {"paid", "completed"}
ACTIVE_SUBSCRIPTION_STATUSES = {"active", "trialing"}
REVOKING_ADJUSTMENTS = {"refund", "chargeback"}


def _parse_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class EntitlementStore:
    def __init__(self, engine: Engine, price_id: str, scans_per_purchase: int):
        self.engine = engine
        self.price_id = price_id
        self.scans_per_purchase = scans_per_purchase

    def _matching_items(self, entity: dict) -> list:
        items = entity.get("items") or []
        if not self.price_id:
            return items
        return [item for item in items
                if (item.get("price") or {}).get("id") == self.price_id or item.get("price_id") == self.price_id]

    def transaction_has_price(self, transaction: dict) -> bool:
        return bool(self._matching_items(transaction))

    def awaiting_subscription(self, transaction: dict) -> bool:
        """A paid recurring checkout whose subscription Paddle hasn't created yet."""
        if transaction.get("subscription_id"):
            return False
        return any((item.get("price") or {}).get("billing_cycle") for item in self._matching_items(transaction))

    def record_transaction(self, transaction: dict) -> Optional[str]:
        """Store a paid transaction idempotently. Returns the customer id if it grants access."""
        transaction_id = transaction.get("id")
        customer_id = transaction.get("customer_id")
        status = transaction.get("status")
        if not transaction_id or not customer_id or status not in PAID_TRANSACTION_STATUSES:
            return None
        if not self.transaction_has_price(transaction):
            logger.warning("Transaction %s does not include the configured price", transaction_id)
            return None
        if self.awaiting_subscription(transaction):
            return None  # recorded once transaction.completed carries the subscription_id

        subscription_id = transaction.get("subscription_id")
        scans = 0 if subscription_id else self.scans_per_purchase
        try:
            with self.engine.begin() as conn:
                conn.execute(purchases.insert().values(
                    transaction_id=transaction_id, customer_id=customer_id,
                    subscription_id=subscription_id, status=status, scans_granted=scans,
                ))
                if scans:
                    self._add_credits(conn, customer_id, scans)
                if subscription_id:
                    self._upsert_subscription(conn, subscription_id, customer_id, "active", only_if_missing=True)
        except IntegrityError:
            pass  # already recorded (checkout claim and webhook can race)
        return customer_id

    def record_subscription(self, subscription: dict, occurred_at: Optional[str] = None) -> None:
        subscription_id = subscription.get("id")
        customer_id = subscription.get("customer_id")
        status = subscription.get("status")
        if not subscription_id or not customer_id or not status:
            return
        if not self._matching_items(subscription):
            status = "canceled"  # not (or no longer) a Measulor plan
        version = subscription.get("updated_at") or occurred_at
        with self.engine.begin() as conn:
            row = conn.execute(select(subscriptions).where(
                subscriptions.c.subscription_id == subscription_id)).first()
            incoming, stored = _parse_time(version), _parse_time(row.paddle_updated_at if row else None)
            if incoming and stored and incoming < stored:
                logger.info("Ignoring out-of-order update for %s", subscription_id)
                return
            self._upsert_subscription(conn, subscription_id, customer_id, status, version=version)

    def record_refund(self, adjustment: dict) -> None:
        action = adjustment.get("action")
        if adjustment.get("status") != "approved":
            return
        transaction_id = adjustment.get("transaction_id")
        if action == "chargeback_reverse":
            self._restore_purchase(transaction_id)
            return
        if action not in REVOKING_ADJUSTMENTS:
            return
        with self.engine.begin() as conn:
            row = conn.execute(select(purchases).where(purchases.c.transaction_id == transaction_id)).first()
            if not row or row.status == "refunded":
                return
            conn.execute(update(purchases).where(purchases.c.transaction_id == transaction_id)
                         .values(status="refunded"))
            if row.scans_granted:
                balance = self.balance(row.customer_id, conn)
                conn.execute(update(credits).where(credits.c.customer_id == row.customer_id)
                             .values(balance=max(0, balance - row.scans_granted)))

    def _restore_purchase(self, transaction_id: str) -> None:
        with self.engine.begin() as conn:
            row = conn.execute(select(purchases).where(purchases.c.transaction_id == transaction_id)).first()
            if not row or row.status != "refunded":
                return
            conn.execute(update(purchases).where(purchases.c.transaction_id == transaction_id)
                         .values(status="paid"))
            if row.scans_granted:
                balance = self.balance(row.customer_id, conn)
                conn.execute(update(credits).where(credits.c.customer_id == row.customer_id)
                             .values(balance=balance + row.scans_granted))

    def mark_event_processed(self, event_id: str, event_type: str) -> bool:
        """Return False if this webhook event was already handled."""
        try:
            with self.engine.begin() as conn:
                conn.execute(webhook_events.insert().values(event_id=event_id, event_type=event_type))
            return True
        except IntegrityError:
            return False

    def unmark_event(self, event_id: str) -> None:
        with self.engine.begin() as conn:
            conn.execute(webhook_events.delete().where(webhook_events.c.event_id == event_id))

    def balance(self, customer_id: str, conn=None) -> int:
        query = select(credits.c.balance).where(credits.c.customer_id == customer_id)
        if conn is not None:
            value = conn.execute(query).scalar()
        else:
            with self.engine.connect() as c:
                value = c.execute(query).scalar()
        return int(value or 0)

    def active_subscription_ids(self, customer_id: str) -> list:
        with self.engine.connect() as conn:
            rows = conn.execute(select(subscriptions.c.subscription_id).where(
                subscriptions.c.customer_id == customer_id,
                subscriptions.c.status.in_(ACTIVE_SUBSCRIPTION_STATUSES),
            )).all()
        return [row.subscription_id for row in rows]

    def summary(self, customer_id: Optional[str]) -> dict:
        if not customer_id:
            return {"customer": False, "subscription_active": False, "scans_remaining": 0, "can_scan": False}
        subscribed = bool(self.active_subscription_ids(customer_id))
        remaining = self.balance(customer_id)
        return {
            "customer": True,
            "subscription_active": subscribed,
            "scans_remaining": remaining,
            "can_scan": subscribed or remaining > 0,
        }

    def consume(self, customer_id: str) -> Optional[str]:
        """Use one scan. Returns "subscription", "credit", or None if not entitled."""
        if self.active_subscription_ids(customer_id):
            return "subscription"
        with self.engine.begin() as conn:
            result = conn.execute(update(credits).where(
                credits.c.customer_id == customer_id, credits.c.balance > 0,
            ).values(balance=credits.c.balance - 1))
        return "credit" if result.rowcount == 1 else None

    def refund_credit(self, customer_id: str) -> None:
        with self.engine.begin() as conn:
            self._add_credits(conn, customer_id, 1)

    @staticmethod
    def _add_credits(conn, customer_id: str, amount: int) -> None:
        result = conn.execute(update(credits).where(credits.c.customer_id == customer_id)
                              .values(balance=credits.c.balance + amount))
        if result.rowcount == 0:
            conn.execute(credits.insert().values(customer_id=customer_id, balance=amount))

    @staticmethod
    def _upsert_subscription(conn, subscription_id, customer_id, status, only_if_missing=False, version=None):
        exists = conn.execute(select(subscriptions.c.subscription_id)
                              .where(subscriptions.c.subscription_id == subscription_id)).first()
        if exists:
            if not only_if_missing:
                conn.execute(update(subscriptions).where(subscriptions.c.subscription_id == subscription_id)
                             .values(status=status, customer_id=customer_id, paddle_updated_at=version,
                                     updated_at=utcnow()))
        else:
            conn.execute(subscriptions.insert().values(
                subscription_id=subscription_id, customer_id=customer_id, status=status,
                paddle_updated_at=version))
