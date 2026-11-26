"""Photos -> body measurements using MediaPipe Pose landmarks.

Height is estimated from MediaPipe world landmarks (metric 3D). Horizontal
widths come from shoulder/hip landmarks; circumferences and some lengths use
anthropometric ratios of stature when not measured directly.
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
L_EAR, R_EAR = 7, 8
L_SHOULDER, R_SHOULDER = 11, 12
L_ELBOW, R_ELBOW = 13, 14
L_WRIST, R_WRIST = 15, 16
L_HIP, R_HIP = 23, 24
L_KNEE, R_KNEE = 25, 26
L_ANKLE, R_ANKLE = 27, 28
L_HEEL, R_HEEL = 29, 30
L_FOOT, R_FOOT = 31, 32

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
    method: str  # measured | estimated

    def to_dict(self) -> dict:
        return {"value_cm": round(float(self.value_cm), 1), "method": self.method}


def _dist(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a - b))


def _xy(landmarks, index: int, width: int, height: int) -> Optional[np.ndarray]:
    lm = landmarks[index]
    if lm.visibility is not None and lm.visibility < 0.5:
        return None
    return np.array([lm.x * width, lm.y * height], dtype=np.float64)


def _world_xyz(world_landmarks, index: int) -> Optional[np.ndarray]:
    lm = world_landmarks[index]
    if lm.visibility is not None and lm.visibility < 0.3:
        return None
    return np.array([lm.x, lm.y, lm.z], dtype=np.float64)


def _pose(image: np.ndarray):
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
        return None, None
    world = result.pose_world_landmarks.landmark if result.pose_world_landmarks else None
    return result.pose_landmarks.landmark, world


def _estimate_height_cm(world_lm) -> Optional[float]:
    """Estimate stature in cm from MediaPipe world landmarks (metres, hip-centred)."""
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
        # Fallback: full vertical span of visible landmarks
        ys = []
        for i in range(33):
            p = _world_xyz(world_lm, i)
            if p is not None:
                ys.append(p[1])
        if len(ys) < 5:
            return None
        span_m = abs(max(ys) - min(ys))
    else:
        # World Y is vertical; direction can vary by MediaPipe version
        span_m = abs(max(head_ys) - min(foot_ys))
        if abs(min(head_ys) - max(foot_ys)) > span_m:
            span_m = abs(min(head_ys) - max(foot_ys))

    # Nose/ear is below crown; ankle/heel is above sole
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
    for idx in (L_ANKLE, R_ANKLE, L_HEEL, R_HEEL):
        p = _xy(lm, idx, w, h)
        if p is not None:
            bottom_candidates.append(p[1])
    if not top_candidates or not bottom_candidates:
        return None
    span = max(bottom_candidates) - min(top_candidates)
    return span if span > 20 else None


def _measure_from_landmarks(
    lm, world_lm, w: int, h: int
) -> Optional[Dict[str, Measurement]]:
    height_cm = _estimate_height_cm(world_lm)
    body_px = _body_height_px(lm, w, h)
    if height_cm is None or body_px is None:
        return None

    scale = height_cm / body_px  # px -> cm (image plane)

    results: Dict[str, Measurement] = {
        "height": Measurement(height_cm, "estimated"),
    }

    # Prefer world-landmark metric widths when available
    def world_width(i: int, j: int) -> Optional[float]:
        a, b = _world_xyz(world_lm, i), _world_xyz(world_lm, j)
        if a is None or b is None:
            return None
        return _dist(a, b) * 100.0  # m -> cm

    shoulder_cm = world_width(L_SHOULDER, R_SHOULDER)
    if shoulder_cm is None:
        l_sh, r_sh = _xy(lm, L_SHOULDER, w, h), _xy(lm, R_SHOULDER, w, h)
        if l_sh is not None and r_sh is not None:
            shoulder_cm = _dist(l_sh, r_sh) * scale
    if shoulder_cm is not None:
        results["shoulder_width"] = Measurement(shoulder_cm, "measured")
        results["chest_circumference"] = Measurement(
            max(shoulder_cm * 2.15, height_cm * 0.45), "measured"
        )

    hip_w = world_width(L_HIP, R_HIP)
    if hip_w is None:
        l_hip, r_hip = _xy(lm, L_HIP, w, h), _xy(lm, R_HIP, w, h)
        if l_hip is not None and r_hip is not None:
            hip_w = _dist(l_hip, r_hip) * scale
    if hip_w is not None:
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
    if torso is not None:
        results["torso_length"] = Measurement(torso, "measured")

    for name, ratio in RATIOS.items():
        if name not in results:
            results[name] = Measurement(height_cm * ratio, "estimated")

    return results


def compute_from_photos(images: List[np.ndarray]) -> dict:
    if not images:
        raise MeasurementError("No photos to measure")

    best: Optional[Tuple[int, Dict[str, Measurement]]] = None
    for i, image in enumerate(images):
        h, w = image.shape[:2]
        landmarks, world = _pose(image)
        if landmarks is None:
            logger.info("No pose detected in photo %d", i)
            continue
        measured = _measure_from_landmarks(landmarks, world, w, h)
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
