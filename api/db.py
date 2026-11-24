"""Database schema and engine (SQLite by default, any SQLAlchemy URL supported)."""

from datetime import datetime, timezone

from sqlalchemy import (
    Column, DateTime, Integer, MetaData, String, Table, Text, create_engine, event,
)
from sqlalchemy.engine import Engine

metadata = MetaData()


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


jobs = Table(
    "jobs", metadata,
    Column("id", String(36), primary_key=True),
    Column("owner_id", String(64), nullable=False, index=True),
    Column("customer_id", String(64)),
    Column("status", String(16), nullable=False, index=True),
    Column("stage", String(32), nullable=False),
    Column("reference_height_cm", Integer, nullable=False),
    Column("video_path", Text),
    Column("result_json", Text),
    Column("error", Text),
    Column("charged", Integer, nullable=False, default=0),
    Column("created_at", DateTime, nullable=False, default=utcnow),
    Column("updated_at", DateTime, nullable=False, default=utcnow, onupdate=utcnow),
)

purchases = Table(
    "purchases", metadata,
    Column("transaction_id", String(64), primary_key=True),
    Column("customer_id", String(64), nullable=False, index=True),
    Column("subscription_id", String(64)),
    Column("status", String(32), nullable=False),
    Column("scans_granted", Integer, nullable=False, default=0),
    Column("created_at", DateTime, nullable=False, default=utcnow),
)

subscriptions = Table(
    "subscriptions", metadata,
    Column("subscription_id", String(64), primary_key=True),
    Column("customer_id", String(64), nullable=False, index=True),
    Column("status", String(32), nullable=False),
    Column("paddle_updated_at", String(40)),
    Column("updated_at", DateTime, nullable=False, default=utcnow, onupdate=utcnow),
)

credits = Table(
    "credits", metadata,
    Column("customer_id", String(64), primary_key=True),
    Column("balance", Integer, nullable=False, default=0),
)

webhook_events = Table(
    "webhook_events", metadata,
    Column("event_id", String(64), primary_key=True),
    Column("event_type", String(64), nullable=False),
    Column("received_at", DateTime, nullable=False, default=utcnow),
)


def make_engine(url: str) -> Engine:
    connect_args = {"check_same_thread": False, "timeout": 30} if url.startswith("sqlite") else {}
    engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True, future=True)
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_conn, _):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()
    metadata.create_all(engine)
    return engine
