"""Module 1 - Video: upload validation, probing and frame selection."""

import logging
import os
import uuid
from dataclasses import dataclass
from typing import List

import cv2
import numpy as np
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {"mp4", "mov", "avi", "webm", "mkv", "m4v"}
MIN_FRAMES_REQUIRED = 10
MIN_DURATION_SECONDS = 3
MIN_SHARPNESS = 40.0
MIN_BRIGHTNESS = 30.0
MAX_BRIGHTNESS = 230.0


class VideoError(ValueError):
    """Raised when a video cannot be accepted or processed."""


@dataclass
class VideoInfo:
    fps: float
    frame_count: int
    duration: float
    width: int
    height: int

    def to_dict(self) -> dict:
        return {
            "fps": round(self.fps, 2),
            "frame_count": self.frame_count,
            "duration_seconds": round(self.duration, 2),
            "resolution": f"{self.width}x{self.height}",
        }


def save_upload(file: FileStorage, upload_dir: str) -> str:
    """Validate the uploaded file's name and store it under a random name."""
    filename = secure_filename(file.filename or "")
    if "." not in filename:
        raise VideoError("Missing file extension")
    extension = filename.rsplit(".", 1)[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise VideoError(f"Unsupported format. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}")
    os.makedirs(upload_dir, exist_ok=True)
    path = os.path.join(upload_dir, f"{uuid.uuid4().hex}.{extension}")
    file.save(path)
    if os.path.getsize(path) == 0:
        os.remove(path)
        raise VideoError("Uploaded file is empty")
    return path


def probe(video_path: str, max_duration_seconds: int) -> VideoInfo:
    """Read video metadata and enforce duration limits."""
    cap = cv2.VideoCapture(video_path)
    try:
        if not cap.isOpened():
            raise VideoError("Could not decode video file")
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    finally:
        cap.release()
    if fps <= 0 or frame_count <= 0 or width <= 0 or height <= 0:
        raise VideoError("Video has no readable frames")
    duration = frame_count / fps
    if duration < MIN_DURATION_SECONDS:
        raise VideoError(f"Video is too short ({duration:.1f}s). Record at least {MIN_DURATION_SECONDS}s")
    if duration > max_duration_seconds:
        raise VideoError(f"Video is too long ({duration:.0f}s). Maximum is {max_duration_seconds}s")
    return VideoInfo(fps=fps, frame_count=frame_count, duration=duration, width=width, height=height)


def frame_quality(frame: np.ndarray) -> dict:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    brightness = float(np.mean(gray))
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    return {
        "brightness": brightness,
        "sharpness": sharpness,
        "usable": MIN_BRIGHTNESS < brightness < MAX_BRIGHTNESS and sharpness >= MIN_SHARPNESS,
    }


def _resize(frame: np.ndarray, max_dimension: int) -> np.ndarray:
    height, width = frame.shape[:2]
    scale = max_dimension / float(max(height, width))
    if scale >= 1.0:
        return frame
    return cv2.resize(frame, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA)


def extract_frames(video_path: str, info: VideoInfo, max_frames: int, max_dimension: int) -> List[np.ndarray]:
    """Sample frames evenly across the whole video, dropping blurry or badly lit ones.

    Twice as many candidates as needed are sampled so that rejected frames can be replaced.
    """
    candidates = min(info.frame_count, max_frames * 2)
    indices = set(np.linspace(0, info.frame_count - 1, candidates).astype(int).tolist())
    cap = cv2.VideoCapture(video_path)
    scored = []
    try:
        index = 0
        while True:
            ok = cap.grab()
            if not ok:
                break
            if index in indices:
                ok, frame = cap.retrieve()
                if ok:
                    quality = frame_quality(frame)
                    if quality["usable"]:
                        scored.append((index, quality["sharpness"], _resize(frame, max_dimension)))
            index += 1
    finally:
        cap.release()

    if len(scored) > max_frames:
        # Keep temporal coverage: split into max_frames buckets and keep the sharpest of each.
        buckets = np.array_split(np.arange(len(scored)), max_frames)
        scored = [max((scored[i] for i in bucket), key=lambda item: item[1]) for bucket in buckets if len(bucket)]

    frames = [frame for _, _, frame in sorted(scored, key=lambda item: item[0])]
    logger.info("Selected %d usable frames from %s", len(frames), video_path)
    if len(frames) < MIN_FRAMES_REQUIRED:
        raise VideoError(
            f"Only {len(frames)} usable frames found (need {MIN_FRAMES_REQUIRED}). "
            "Record in good lighting and move the camera slowly around the person."
        )
    return frames
