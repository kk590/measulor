"""Photos -> body measurements using MediaPipe Pose landmarks.

Height is estimated from MediaPipe world landmarks (metric 3D). Horizontal
widths come from shoulder/hip landmarks; circumferences and some lengths use
anthropometric ratios of stature when not measured directly.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

try:
    import mediapipe as mp
except ImportError:  # pragma: no cover
    mp = None

logger = logging.getLogger(__name__)

MIN_HEIGHT_CM = 80
MAX_HEIGHT_CM = 250
DEFAULT_HEIGHT_CM = 170.0

NOSE = 0
L_EAR, R_EAR = 7, 8
L_SHOULDER, R_SHOULDER = 11, 12
L_ELBOW, R_ELBOW = 13, 14
L_WRIST, R_WRIST = 15, 16
L_HIP, R_HIP = 23, 24
L_KNEE, R_KNEE = 25, 26
L_ANKLE, R_ANKLE = 27, 28
L_HEEL, R_HEEL = 29, 30
L_FOOT, R_FOOT = 31, 32

RATIOS = {
    "chest_circumference": 0.555,
    "waist_circumference": 0.465,
    "hip_circumference": 0.565,
    "thigh_circumference": 0.325,
    "arm_length": 0.440,
    "torso_length": 0.300,
    "inseam": 0.450,
    "leg_length": 0.530,
}

_pose_lock = threading.Lock()
_pose_instance = None
_pose_init_error: Optional[str] = None


class MeasurementError(ValueError):
    """Raised when measurements cannot be computed from photos."""


@dataclass
class Measurement:
    value_cm: float
    method: str

    def to_dict(self) -> dict:
        return {"value_cm": round(float(self.value_cm), 1), "method": self.method}


def _dist(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a - b))


def _visibility(lm) -> float:
    try:
        v = getattr(lm, "visibility", None)
        if v is None:
            return 1.0
        return float(v)
    except Exception:
        return 1.0


def _xy(landmarks, index: int, width: int, height: int, min_vis: float = 0.3) -> Optional[np.ndarray]:
    try:
        lm = landmarks[index]
    except Exception:
        return None
    if _visibility(lm) < min_vis:
        return None
    try:
        return np.array([float(lm.x) * width, float(lm.y) * height], dtype=np.float64)
    except Exception:
        return None


def _world_xyz(world_landmarks, index: int, min_vis: float = 0.15) -> Optional[np.ndarray]:
    if world_landmarks is None:
        return None
    try:
        lm = world_landmarks[index]
    except Exception:
        return None
    if _visibility(lm) < min_vis:
        return None
    try:
        return np.array([float(lm.x), float(lm.y), float(lm.z)], dtype=np.float64)
    except Exception:
        return None


def _to_rgb_uint8(image: np.ndarray) -> np.ndarray:
    """MediaPipe requires contiguous RGB uint8 HWC."""
    if image is None or getattr(image, "size", 0) == 0:
        raise MeasurementError("Empty image")
    arr = np.asarray(image)
    if arr.ndim == 2:
        arr = cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
    elif arr.ndim == 3 and arr.shape[2] == 4:
        arr = cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)
    elif arr.ndim != 3 or arr.shape[2] != 3:
        raise MeasurementError(f"Unsupported image shape {getattr(arr, 'shape', None)}")

    if arr.dtype != np.uint8:
        arr = np.clip(arr, 0, 255).astype(np.uint8)

    # OpenCV loads BGR; convert to RGB for MediaPipe
    rgb = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)
    if not rgb.flags["C_CONTIGUOUS"]:
        rgb = np.ascontiguousarray(rgb)
    return rgb


def _get_pose():
    """Lazy singleton Pose — creating/closing per image is slow and flaky under gunicorn threads."""
    global _pose_instance, _pose_init_error
    if _pose_instance is not None:
        return _pose_instance
    if _pose_init_error is not None:
        raise MeasurementError(_pose_init_error)

    with _pose_lock:
        if _pose_instance is not None:
            return _pose_instance
        if _pose_init_error is not None:
            raise MeasurementError(_pose_init_error)

        if mp is None:
            _pose_init_error = "mediapipe is not installed on this server"
            raise MeasurementError(_pose_init_error)

        solutions = getattr(mp, "solutions", None)
        if solutions is None or not hasattr(solutions, "pose"):
            _pose_init_error = (
                "MediaPipe Pose is unavailable. Redeploy with mediapipe 0.10.9–0.10.14"
            )
            raise MeasurementError(_pose_init_error)

        try:
            _pose_instance = solutions.pose.Pose(
                static_image_mode=True,
                model_complexity=0,
                enable_segmentation=False,
                min_detection_confidence=0.35,
                min_tracking_confidence=0.35,
            )
            # Warm-up so first user request does not pay model-load cost / race
            blank = np.zeros((256, 192, 3), dtype=np.uint8)
            _pose_instance.process(blank)
            logger.info("MediaPipe Pose initialised")
        except Exception as exc:
            logger.exception("Failed to initialise MediaPipe Pose")
            _pose_init_error = f"Pose engine failed to start: {type(exc).__name__}: {exc}"
            _pose_instance = None
            raise MeasurementError(_pose_init_error) from exc

        return _pose_instance


def _pose(image: np.ndarray):
    rgb = _to_rgb_uint8(image)
    pose = _get_pose()

    with _pose_lock:
        try:
            result = pose.process(rgb)
        except Exception as exc:
            logger.exception("MediaPipe pose.process failed")
            # Recreate once in case the graph is in a bad state
            global _pose_instance
            try:
                if _pose_instance is not None:
                    _pose_instance.close()
            except Exception:
                pass
            _pose_instance = None
            try:
                pose = _get_pose()
                result = pose.process(rgb)
            except Exception as exc2:
                logger.exception("MediaPipe pose retry failed")
                raise MeasurementError(
                    f"Pose detection failed ({type(exc2).__name__}). "
                    "Try another photo or redeploy the backend."
                ) from exc2

    if not result or not getattr(result, "pose_landmarks", None):
        return None, None

    landmarks = result.pose_landmarks.landmark
    world = None
    if getattr(result, "pose_world_landmarks", None):
        world = result.pose_world_landmarks.landmark
    return landmarks, world


def _estimate_height_cm(world_lm) -> Optional[float]:
    if world_lm is None:
        return None

    head_idxs = (NOSE, L_EAR, R_EAR, L_SHOULDER, R_SHOULDER)
    foot_idxs = (L_ANKLE, R_ANKLE, L_HEEL, R_HEEL, L_FOOT, R_FOOT)

    head_ys = []
    for idx in head_idxs:
        p = _world_xyz(world_lm, idx)
        if p is not None:
            head_ys.append(p[1])
    foot_ys = []
    for idx in foot_idxs:
        p = _world_xyz(world_lm, idx)
        if p is not None:
            foot_ys.append(p[1])

    if not head_ys or not foot_ys:
        ys = []
        for i in range(33):
            p = _world_xyz(world_lm, i)
            if p is not None:
                ys.append(p[1])
        if len(ys) < 5:
            return None
        span_m = abs(max(ys) - min(ys))
    else:
        span_m = abs(max(head_ys) - min(foot_ys))
        alt = abs(min(head_ys) - max(foot_ys))
        if alt > span_m:
            span_m = alt

    height_cm = span_m * 100.0 + 12.0
    if height_cm < 50 or height_cm > 280:
        return None
    return float(max(MIN_HEIGHT_CM, min(MAX_HEIGHT_CM, height_cm)))


def _body_height_px(lm, w: int, h: int) -> Optional[float]:
    top_candidates = []
    for idx in (NOSE, L_SHOULDER, R_SHOULDER):
        p = _xy(lm, idx, w, h)
        if p is not None:
            top_candidates.append(p[1])
    bottom_candidates = []
    for idx in (L_ANKLE, R_ANKLE, L_HEEL, R_HEEL, L_FOOT, R_FOOT, L_KNEE, R_KNEE):
        p = _xy(lm, idx, w, h)
        if p is not None:
            bottom_candidates.append(p[1])
    if not top_candidates or not bottom_candidates:
        return None
    span = max(bottom_candidates) - min(top_candidates)
    return span if span > 20 else None


def _measure_from_landmarks(lm, world_lm, w: int, h: int) -> Optional[Dict[str, Measurement]]:
    body_px = _body_height_px(lm, w, h)
    if body_px is None:
        return None

    height_cm = _estimate_height_cm(world_lm)
    if height_cm is None:
        height_cm = DEFAULT_HEIGHT_CM

    scale = height_cm / body_px
    results: Dict[str, Measurement] = {
        "height": Measurement(height_cm, "estimated"),
    }

    def world_width(i: int, j: int) -> Optional[float]:
        a, b = _world_xyz(world_lm, i), _world_xyz(world_lm, j)
        if a is None or b is None:
            return None
        return _dist(a, b) * 100.0

    shoulder_cm = world_width(L_SHOULDER, R_SHOULDER)
    if shoulder_cm is None:
        l_sh, r_sh = _xy(lm, L_SHOULDER, w, h), _xy(lm, R_SHOULDER, w, h)
        if l_sh is not None and r_sh is not None:
            shoulder_cm = _dist(l_sh, r_sh) * scale
    if shoulder_cm is not None and shoulder_cm > 0:
        results["shoulder_width"] = Measurement(shoulder_cm, "measured")
        results["chest_circumference"] = Measurement(
            max(shoulder_cm * 2.15, height_cm * 0.45), "measured"
        )

    hip_w = world_width(L_HIP, R_HIP)
    if hip_w is None:
        l_hip, r_hip = _xy(lm, L_HIP, w, h), _xy(lm, R_HIP, w, h)
        if l_hip is not None and r_hip is not None:
            hip_w = _dist(l_hip, r_hip) * scale
    if hip_w is not None and hip_w > 0:
        results["hip_width"] = Measurement(hip_w, "measured")
        results["hip_circumference"] = Measurement(
            max(hip_w * 2.45, height_cm * 0.48), "measured"
        )
        results["waist_circumference"] = Measurement(
            max(hip_w * 2.05, height_cm * 0.40), "measured"
        )

    arms = []
    for sh, wr in ((L_SHOULDER, L_WRIST), (R_SHOULDER, R_WRIST)):
        a, b = _world_xyz(world_lm, sh), _world_xyz(world_lm, wr)
        if a is not None and b is not None:
            arms.append(_dist(a, b) * 100.0)
        else:
            pa, pb = _xy(lm, sh, w, h), _xy(lm, wr, w, h)
            if pa is not None and pb is not None:
                arms.append(_dist(pa, pb) * scale)
    if arms:
        results["arm_length"] = Measurement(float(np.mean(arms)), "measured")

    legs = []
    for hip, ankle in ((L_HIP, L_ANKLE), (R_HIP, R_ANKLE)):
        a, b = _world_xyz(world_lm, hip), _world_xyz(world_lm, ankle)
        if a is not None and b is not None:
            legs.append(_dist(a, b) * 100.0)
        else:
            pa, pb = _xy(lm, hip, w, h), _xy(lm, ankle, w, h)
            if pa is not None and pb is not None:
                legs.append(_dist(pa, pb) * scale)
    if legs:
        results["inseam"] = Measurement(float(np.mean(legs)), "measured")
        results["leg_length"] = Measurement(float(np.mean(legs)) * 1.12, "measured")

    torso = world_width(L_SHOULDER, L_HIP) or world_width(R_SHOULDER, R_HIP)
    if torso is None:
        l_sh, l_hip = _xy(lm, L_SHOULDER, w, h), _xy(lm, L_HIP, w, h)
        r_sh, r_hip = _xy(lm, R_SHOULDER, w, h), _xy(lm, R_HIP, w, h)
        if l_sh is not None and l_hip is not None:
            torso = _dist(l_sh, l_hip) * scale
        elif r_sh is not None and r_hip is not None:
            torso = _dist(r_sh, r_hip) * scale
    if torso is not None and torso > 0:
        results["torso_length"] = Measurement(torso, "measured")

    for name, ratio in RATIOS.items():
        if name not in results:
            results[name] = Measurement(height_cm * ratio, "estimated")

    return results


def compute_from_photos(images: List[np.ndarray]) -> dict:
    if not images:
        raise MeasurementError("No photos to measure")

    # Ensure pose engine can start before looping images
    try:
        _get_pose()
    except MeasurementError:
        raise

    best: Optional[Tuple[int, Dict[str, Measurement]]] = None
    last_error: Optional[str] = None

    for i, image in enumerate(images):
        try:
            if image is None or getattr(image, "size", 0) == 0:
                last_error = f"Photo {i + 1} is empty or unreadable"
                continue
            h, w = image.shape[:2]
            landmarks, world = _pose(image)
            if landmarks is None:
                logger.info("No pose detected in photo %d", i)
                last_error = "No full-body pose detected in the photo"
                continue
            measured = _measure_from_landmarks(landmarks, world, w, h)
            if measured is None:
                last_error = "Pose found but body landmarks incomplete (need head-to-feet visible)"
                continue
            score = sum(1 for m in measured.values() if m.method == "measured")
            if best is None or score > best[0]:
                best = (score, measured)
        except MeasurementError as exc:
            last_error = str(exc).rstrip(".")
            logger.warning("Photo %d measurement error: %s", i, exc)
        except Exception:
            logger.exception("Unexpected failure on photo %d", i)
            last_error = "Unexpected failure while analysing a photo"

    if best is None:
        detail = (last_error or "Could not detect a full body pose").rstrip(".")
        tip = "Use a clear full-body photo, A-pose, bright even lighting, head to feet visible"
        if tip.lower() in detail.lower():
            raise MeasurementError(detail + ".")
        raise MeasurementError(f"{detail}. {tip}.")

    score, results = best
    confidence = "high" if score >= 6 else "medium" if score >= 3 else "low"
    logger.info("Photo measurements: %d measured values, confidence=%s", score, confidence)
    return {
        "unit": "cm",
        "confidence": confidence,
        "photos_used": len(images),
        "measurements": {name: m.to_dict() for name, m in results.items()},
    }
