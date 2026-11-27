"""Orchestrates the pipeline: photos -> body measurements."""

import logging
from typing import Callable, List

from .config import Config
from .modules import photo_measurements, photos

logger = logging.getLogger(__name__)

STAGES = ("photos", "pose", "measurements")


class PipelineError(RuntimeError):
    """User-facing pipeline failure."""


def run(photo_paths: List[str], work_dir: str, config: Config,
        on_stage: Callable[[str], None] = lambda stage: None) -> dict:
    try:
        on_stage("photos")
        images = photos.load_images(photo_paths)

        on_stage("pose")
        on_stage("measurements")
        result = photo_measurements.compute_from_photos(images)
    except (photos.PhotoError, photo_measurements.MeasurementError) as exc:
        raise PipelineError(str(exc)) from exc
    except Exception as exc:
        logger.exception("Pipeline crashed")
        raise PipelineError(
            str(exc).strip() or "Could not process the photos"
        ) from exc

    return {
        "photos": {"count": len(photo_paths)},
        **result,
    }
