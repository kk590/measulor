"""Background job execution and persistence for pipeline runs."""

import json
import logging
import os
import shutil
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from typing import Callable, Optional

from sqlalchemy import select, update
from sqlalchemy.engine import Engine

from .config import Config
from .db import jobs, utcnow
from .modules.payments import EntitlementStore
from .pipeline import PipelineError

logger = logging.getLogger(__name__)


class JobService:
    def __init__(self, engine: Engine, config: Config, entitlements: EntitlementStore,
                 runner: Callable[..., dict]):
        self.engine = engine
        self.config = config
        self.entitlements = entitlements
        self.runner = runner
        self.executor = ThreadPoolExecutor(max_workers=config.worker_threads, thread_name_prefix="pipeline")
        self.jobs_dir = os.path.join(config.data_dir, "jobs")
        os.makedirs(self.jobs_dir, exist_ok=True)
        self._recover_interrupted()
        self._stop = threading.Event()
        threading.Thread(target=self._cleanup_loop, name="artifact-cleanup", daemon=True).start()

    def _cleanup_loop(self, interval_seconds: int = 3600) -> None:
        while not self._stop.wait(interval_seconds):
            try:
                self.cleanup_expired()
            except Exception:
                logger.exception("Artifact cleanup failed")

    def job_dir(self, job_id: str) -> str:
        return os.path.join(self.jobs_dir, job_id)

    def create(self, owner_id: str, video_path: str, reference_height_cm: float,
               customer_id: Optional[str], charge: Optional[str]) -> str:
        job_id = str(uuid.uuid4())
        os.makedirs(self.job_dir(job_id), exist_ok=True)
        with self.engine.begin() as conn:
            conn.execute(jobs.insert().values(
                id=job_id, owner_id=owner_id, status="queued", stage="queued",
                reference_height_cm=int(round(reference_height_cm)), video_path=video_path,
                customer_id=customer_id, charged=1 if charge == "credit" else 0,
            ))
        self.executor.submit(self._execute, job_id, video_path, reference_height_cm)
        self.cleanup_expired()
        return job_id

    def get(self, job_id: str, owner_id: str) -> Optional[dict]:
        with self.engine.connect() as conn:
            row = conn.execute(select(jobs).where(jobs.c.id == job_id, jobs.c.owner_id == owner_id)).first()
        if not row:
            return None
        return {
            "id": row.id,
            "status": row.status,
            "stage": row.stage,
            "reference_height_cm": row.reference_height_cm,
            "result": json.loads(row.result_json) if row.result_json else None,
            "error": row.error if row.status == "failed" else None,
            "has_model": row.status == "completed" and os.path.exists(self.model_path(row.id)),
            "created_at": row.created_at.isoformat() + "Z",
        }

    def model_path(self, job_id: str) -> str:
        return os.path.join(self.job_dir(job_id), "model.ply")

    def _set(self, job_id: str, **values) -> None:
        with self.engine.begin() as conn:
            conn.execute(update(jobs).where(jobs.c.id == job_id).values(updated_at=utcnow(), **values))

    def _execute(self, job_id: str, video_path: str, reference_height_cm: float):
        started = time.monotonic()
        self._set(job_id, status="running", stage="video")
        try:
            result = self.runner(video_path, reference_height_cm, self.job_dir(job_id), self.config,
                                 on_stage=lambda stage: self._set(job_id, stage=stage))
            self._set(job_id, status="completed", stage="done", result_json=json.dumps(result), error=None)
            logger.info("Job %s completed in %.1fs", job_id, time.monotonic() - started)
        except PipelineError as exc:
            self._fail(job_id, str(exc))
        except Exception:
            logger.exception("Job %s crashed", job_id)
            self._fail(job_id, "Internal error while processing the video")
        finally:
            if video_path and os.path.exists(video_path):
                os.remove(video_path)
            self._set(job_id, video_path=None)

    def _fail(self, job_id: str, message: str) -> None:
        with self.engine.connect() as conn:
            row = conn.execute(select(jobs.c.charged, jobs.c.customer_id).where(jobs.c.id == job_id)).first()
        if row and row.charged and row.customer_id:
            self.entitlements.refund_credit(row.customer_id)
        self._set(job_id, status="failed", stage="failed", error=message, charged=0)
        logger.info("Job %s failed: %s", job_id, message)

    def _recover_interrupted(self) -> None:
        """Fail jobs left running by a previous process and refund their scan."""
        with self.engine.connect() as conn:
            rows = conn.execute(select(jobs).where(jobs.c.status.in_(("queued", "running")))).all()
        for row in rows:
            self._fail(row.id, "Processing was interrupted by a server restart. Your scan was refunded.")
            if row.video_path and os.path.exists(row.video_path):
                os.remove(row.video_path)

    def cleanup_expired(self) -> None:
        cutoff = utcnow() - timedelta(hours=self.config.keep_artifacts_hours)
        with self.engine.connect() as conn:
            rows = conn.execute(select(jobs.c.id).where(
                jobs.c.created_at < cutoff, jobs.c.status.in_(("completed", "failed")))).all()
        for row in rows:
            shutil.rmtree(self.job_dir(row.id), ignore_errors=True)

    def shutdown(self) -> None:
        self._stop.set()
        self.executor.shutdown(wait=False, cancel_futures=True)
