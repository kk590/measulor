"""Photos -> body measurements using MediaPipe Pose landmarks.

Scale is set from the user's real height. Horizontal widths come from shoulder/hip
landmarks; circumferences and some lengths use anthropometric ratios of stature.
"""

from __future__ import annotations

import logging
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

# Landmark indices (MediaPipe Pose)
NOSE = 0
L_SHOULDER, R_SHOULDER = 11, 12
L_ELBOW, R_ELBOW = 13, 14
L_WRIST, R_WRIST = 15, 16
L_HIP, R_HIP = 23, 24
L_KNEE, R_KNEE = 25, 26
L_ANKLE, R_ANKLE = 27, 28

# Circumference / length as fraction of stature when not measured from width
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


class MeasurementError(ValueError):
    """Raised when measurements cannot be computed from photos."""


@dataclass
class Measurement:
    value_cm: float
    method: str  # reference | measured | estimated

    def to_dict(self) -> dict:
        return {"value_cm": round(float(self.value_cm), 1), "method": self.method}


def _dist(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a - b))


def _xy(landmarks, index: int, width: int, height: int) -> Optional[np.ndarray]:
    lm = landmarks[index]
    if lm.visibility is not None and lm.visibility < 0.5:
        return None
    return np.array([lm.x * width, lm.y * height], dtype=np.float64)


def _pose_landmarks(image: np.ndarray):
    if mp is None:
        raise MeasurementError("mediapipe is not installed on this server")
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    with mp.solutions.pose.Pose(
        static_image_mode=True,
        model_complexity=1,
        enable_segmentation=False,
        min_detection_confidence=0.5,
    ) as pose:
        result = pose.process(rgb)
    if not result.pose_landmarks:
        return None
    return result.pose_landmarks.landmark


def _body_height_px(lm, w: int, h: int) -> Optional[float]:
    """Vertical span nose/shoulder top to ankle as a proxy for stature in pixels."""
    top_candidates = []
    for idx in (NOSE, L_SHOULDER, R_SHOULDER):
        p = _xy(lm, idx, w, h)
        if p is not None:
            top_candidates.append(p[1])
    bottom_candidates = []
    for idx in (L_ANKLE, R_ANKLE, L_KNEE, R_KNEE):
        p = _xy(lm, idx, w, h)
        if p is not None:
            bottom_candidates.append(p[1])
    if not top_candidates or not bottom_candidates:
        return None
    span = max(bottom_candidates) - min(top_candidates)
    return span if span > 20 else None


def _measure_from_landmarks(lm, w: int, h: int, height_cm: float) -> Optional[Dict[str, Measurement]]:
    body_px = _body_height_px(lm, w, h)
    if body_px is None:
        return None
    scale = height_cm / body_px  # px -> cm

    results: Dict[str, Measurement] = {
        "height": Measurement(height_cm, "reference"),
    }

    l_sh = _xy(lm, L_SHOULDER, w, h)
    r_sh = _xy(lm, R_SHOULDER, w, h)
    l_hip = _xy(lm, L_HIP, w, h)
    r_hip = _xy(lm, R_HIP, w, h)

    if l_sh is not None and r_sh is not None:
        shoulder_cm = _dist(l_sh, r_sh) * scale
        results["shoulder_width"] = Measurement(shoulder_cm, "measured")
        results["chest_circumference"] = Measurement(max(shoulder_cm * 2.15, height_cm * 0.45), "measured")

    if l_hip is not None and r_hip is not None:
        hip_w = _dist(l_hip, r_hip) * scale
        results["hip_width"] = Measurement(hip_w, "measured")
        results["hip_circumference"] = Measurement(max(hip_w * 2.45, height_cm * 0.48), "measured")
        results["waist_circumference"] = Measurement(max(hip_w * 2.05, height_cm * 0.40), "measured")

    arms = []
    for sh, wr in ((L_SHOULDER, L_WRIST), (R_SHOULDER, R_WRIST)):
        a, b = _xy(lm, sh, w, h), _xy(lm, wr, w, h)
        if a is not None and b is not None:
            arms.append(_dist(a, b) * scale)
    if arms:
        results["arm_length"] = Measurement(float(np.mean(arms)), "measured")

    legs = []
    for hip, ankle in ((L_HIP, L_ANKLE), (R_HIP, R_ANKLE)):
        a, b = _xy(lm, hip, w, h), _xy(lm, ankle, w, h)
        if a is not None and b is not None:
            legs.append(_dist(a, b) * scale)
    if legs:
        results["inseam"] = Measurement(float(np.mean(legs)), "measured")
        results["leg_length"] = Measurement(float(np.mean(legs)) * 1.12, "measured")

    if l_sh is not None and l_hip is not None:
        results["torso_length"] = Measurement(_dist(l_sh, l_hip) * scale, "measured")
    elif r_sh is not None and r_hip is not None:
        results["torso_length"] = Measurement(_dist(r_sh, r_hip) * scale, "measured")

    for name, ratio in RATIOS.items():
        if name not in results:
            results[name] = Measurement(height_cm * ratio, "estimated")

    return results


def compute_from_photos(images: List[np.ndarray], reference_height_cm: float) -> dict:
    if not MIN_HEIGHT_CM <= reference_height_cm <= MAX_HEIGHT_CM:
        raise MeasurementError(f"Height must be between {MIN_HEIGHT_CM} and {MAX_HEIGHT_CM} cm")
    if not images:
        raise MeasurementError("No photos to measure")

    best: Optional[Tuple[int, Dict[str, Measurement]]] = None
    for i, image in enumerate(images):
        h, w = image.shape[:2]
        landmarks = _pose_landmarks(image)
        if landmarks is None:
            logger.info("No pose detected in photo %d", i)
            continue
        measured = _measure_from_landmarks(landmarks, w, h, reference_height_cm)
        if measured is None:
            continue
        score = sum(1 for m in measured.values() if m.method == "measured")
        if best is None or score > best[0]:
            best = (score, measured)

    if best is None:
        raise MeasurementError(
            "Could not detect a full body pose. Use a clear full-body photo, A-pose, good lighting."
        )

    score, results = best
    confidence = "high" if score >= 6 else "medium" if score >= 3 else "low"
    logger.info("Photo measurements: %d measured values, confidence=%s", score, confidence)
    return {
        "unit": "cm",
        "confidence": confidence,
        "photos_used": len(images),
        "measurements": {name: m.to_dict() for name, m in results.items()},
    }
