"""Orchestrates the pipeline: video -> 3D model -> measurements."""

import logging
from typing import Callable

from .config import Config
from .modules import measurements, reconstruction, video

logger = logging.getLogger(__name__)

STAGES = ("video", "reconstruction", "measurements")


class PipelineError(RuntimeError):
    """User-facing pipeline failure."""


def run(video_path: str, reference_height_cm: float, work_dir: str, config: Config,
        on_stage: Callable[[str], None] = lambda stage: None) -> dict:
    try:
        on_stage("video")
        info = video.probe(video_path, config.max_video_seconds)
        frames = video.extract_frames(video_path, info, config.max_frames, config.frame_max_dimension)

        on_stage("reconstruction")
        model = reconstruction.reconstruct(frames, work_dir)
        del frames

        on_stage("measurements")
        result = measurements.compute_measurements(
            model.points, reference_height_cm,
            camera_centers=model.camera_centers,
            view_directions=model.view_directions,
            up_vectors=model.up_vectors,
        )
    except (video.VideoError, reconstruction.ReconstructionError, measurements.MeasurementError) as exc:
        raise PipelineError(str(exc)) from exc

    return {
        "video": info.to_dict(),
        "model": model.stats(),
        **result,
    }
