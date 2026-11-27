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
from typing import Callable, List, Optional

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

    def create(self, owner_id: str, photo_paths: List[str],
               customer_id: Optional[str], charge: Optional[str]) -> str:
        job_id = str(uuid.uuid4())
        os.makedirs(self.job_dir(job_id), exist_ok=True)
        with self.engine.begin() as conn:
            conn.execute(jobs.insert().values(
                id=job_id, owner_id=owner_id, status="queued", stage="queued",
                reference_height_cm=0,
                video_path=json.dumps(photo_paths),
                customer_id=customer_id, charged=1 if charge == "credit" else 0,
            ))
        self.executor.submit(self._execute, job_id, photo_paths)
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
            "result": json.loads(row.result_json) if row.result_json else None,
            "error": row.error if row.status == "failed" else None,
            "has_model": False,
            "created_at": row.created_at.isoformat() + "Z",
        }

    def _set(self, job_id: str, **values) -> None:
        with self.engine.begin() as conn:
            conn.execute(update(jobs).where(jobs.c.id == job_id).values(updated_at=utcnow(), **values))

    def _execute(self, job_id: str, photo_paths: List[str]):
        started = time.monotonic()
        self._set(job_id, status="running", stage="photos")
        try:
            result = self.runner(photo_paths, self.job_dir(job_id), self.config,
                                 on_stage=lambda stage: self._set(job_id, stage=stage))
            height = 0
            try:
                height = int(round(float(result["measurements"]["height"]["value_cm"])))
            except (KeyError, TypeError, ValueError):
                pass
            self._set(job_id, status="completed", stage="done", result_json=json.dumps(result),
                      error=None, reference_height_cm=height)
            logger.info("Job %s completed in %.1fs", job_id, time.monotonic() - started)
        except PipelineError as exc:
            self._fail(job_id, str(exc) or "Could not process the photos")
        except Exception as exc:
            logger.exception("Job %s crashed", job_id)
            message = str(exc).strip()
            if not message or len(message) > 240:
                message = "Could not process the photos. Try a clear full-body photo (head to feet, A-pose)."
            else:
                message = f"Processing failed: {message}"
            self._fail(job_id, message)
        finally:
            for path in photo_paths:
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except OSError:
                        logger.warning("Could not remove upload %s", path)
            self._set(job_id, video_path=None)

    def _fail(self, job_id: str, message: str) -> None:
        with self.engine.connect() as conn:
            row = conn.execute(select(jobs.c.charged, jobs.c.customer_id).where(jobs.c.id == job_id)).first()
        if row and row.charged and row.customer_id:
            self.entitlements.refund_credit(row.customer_id)
        self._set(job_id, status="failed", stage="failed", error=message, charged=0)
        logger.info("Job %s failed: %s", job_id, message)

    def _recover_interrupted(self) -> None:
        with self.engine.connect() as conn:
            rows = conn.execute(select(jobs).where(jobs.c.status.in_(("queued", "running")))).all()
        for row in rows:
            self._fail(row.id, "Processing was interrupted by a server restart. Your scan was refunded.")
            if row.video_path:
                try:
                    paths = json.loads(row.video_path)
                    if isinstance(paths, list):
                        for p in paths:
                            if p and os.path.exists(p):
                                os.remove(p)
                    elif os.path.exists(row.video_path):
                        os.remove(row.video_path)
                except Exception:
                    if os.path.exists(row.video_path):
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
