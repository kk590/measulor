"""Module 3 - Measurements: body measurements from the reconstructed point cloud.

COLMAP models have no metric scale, so the user's real height is used to scale the cloud.
Circumferences and widths are measured on horizontal slices of the isolated body; values
that cannot be measured reliably fall back to anthropometric ratios and are flagged as
"estimated".
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
from scipy.spatial import cKDTree

logger = logging.getLogger(__name__)

MIN_HEIGHT_CM = 80
MAX_HEIGHT_CM = 250
MIN_SLICE_POINTS = 12
ANGULAR_BINS = 36
MIN_FILLED_BINS = 12
SMOOTHING_BINS = 5
LEG_GAP_FRACTION = 0.08
SLICE_HALF_THICKNESS = 0.015  # fraction of body height

# Landmark heights as a fraction of stature, measured from the floor.
LEVELS = {
    "shoulder": 0.818,
    "chest": 0.720,
    "waist": 0.610,
    "hip": 0.520,
    "thigh": 0.440,
}

# Fallback ratios of stature for lengths that a sparse cloud cannot resolve.
RATIOS = {
    "arm_length": 0.440,
    "torso_length": 0.300,
    "inseam": 0.450,
    "leg_length": 0.530,
}


class MeasurementError(ValueError):
    """Raised when measurements cannot be computed."""


@dataclass
class Measurement:
    value_cm: float
    method: str  # "measured" or "estimated"

    def to_dict(self) -> dict:
        return {"value_cm": round(float(self.value_cm), 1), "method": self.method}


def _remove_outliers(points: np.ndarray, k: int = 12, std_ratio: float = 2.0) -> np.ndarray:
    if len(points) <= k:
        return points
    distances, _ = cKDTree(points).query(points, k=k + 1)
    mean_distance = distances[:, 1:].mean(axis=1)
    keep = mean_distance < mean_distance.mean() + std_ratio * mean_distance.std()
    return points[keep]


def _rays_focus(centers: np.ndarray, directions: np.ndarray) -> Optional[np.ndarray]:
    """Least-squares point closest to all camera viewing rays (where the camera was aimed)."""
    if len(centers) < 2:
        return None
    a = np.zeros((3, 3))
    b = np.zeros(3)
    for center, direction in zip(centers, directions):
        direction = direction / np.linalg.norm(direction)
        projector = np.eye(3) - np.outer(direction, direction)
        a += projector
        b += projector @ center
    try:
        return np.linalg.solve(a, b)
    except np.linalg.LinAlgError:
        return None


def _up_axis(points: np.ndarray, up_vectors: Optional[np.ndarray]) -> np.ndarray:
    if up_vectors is not None and len(up_vectors):
        up = up_vectors.mean(axis=0)
        norm = np.linalg.norm(up)
        if norm > 0.5:  # cameras broadly agree on which way is up
            return up / norm
    centered = points - points.mean(axis=0)
    _, _, vt = np.linalg.svd(centered, full_matrices=False)
    up = vt[0]
    return up if up[1] < 0 else -up  # COLMAP world y usually points down


def _horizontal_basis(up: np.ndarray):
    helper = np.array([1.0, 0.0, 0.0]) if abs(up[0]) < 0.9 else np.array([0.0, 0.0, 1.0])
    u = np.cross(up, helper)
    u /= np.linalg.norm(u)
    v = np.cross(up, u)
    return u, v


def _isolate_subject(height: np.ndarray, planar: np.ndarray, focus_2d: Optional[np.ndarray]) -> np.ndarray:
    """Keep points within a vertical cylinder around the subject's axis."""
    center = focus_2d if focus_2d is not None else np.median(planar, axis=0)
    radial = np.linalg.norm(planar - center, axis=1)
    span = np.percentile(height, 99) - np.percentile(height, 1)
    # A standing adult's horizontal radius is well under 40% of their height.
    return radial < 0.4 * span


def _radial_profile(points_2d: np.ndarray) -> Optional[np.ndarray]:
    """Noise-robust outline of a horizontal slice: median radius per angular bin."""
    if len(points_2d) < MIN_SLICE_POINTS:
        return None
    center = np.median(points_2d, axis=0)
    offsets = points_2d - center
    angles = np.arctan2(offsets[:, 1], offsets[:, 0])
    radii = np.linalg.norm(offsets, axis=1)
    bins = ((angles + np.pi) / (2 * np.pi) * ANGULAR_BINS).astype(int) % ANGULAR_BINS
    medians = np.full(ANGULAR_BINS, np.nan)
    for b in range(ANGULAR_BINS):
        in_bin = radii[bins == b]
        if len(in_bin):
            medians[b] = np.median(in_bin)
    filled = ~np.isnan(medians)
    if filled.sum() < MIN_FILLED_BINS:
        return None
    index = np.arange(ANGULAR_BINS)
    medians = np.interp(index, index[filled], medians[filled], period=ANGULAR_BINS)
    # Circular moving average so per-bin noise doesn't zigzag the outline and inflate the perimeter.
    kernel = np.ones(SMOOTHING_BINS) / SMOOTHING_BINS
    pad = SMOOTHING_BINS // 2
    medians = np.convolve(np.concatenate([medians[-pad:], medians, medians[:pad]]), kernel, mode="valid")
    theta = (index + 0.5) / ANGULAR_BINS * 2 * np.pi - np.pi
    return center + np.stack([medians * np.cos(theta), medians * np.sin(theta)], axis=1)


def _split_legs(points_2d: np.ndarray) -> Optional[List[np.ndarray]]:
    """Split a thigh-level slice into left/right legs at the widest gap across the body axis."""
    if len(points_2d) < 2 * MIN_SLICE_POINTS:
        return None
    centered = points_2d - points_2d.mean(axis=0)
    _, _, vt = np.linalg.svd(centered, full_matrices=False)
    projected = centered @ vt[0]
    order = np.sort(projected)
    lo, hi = np.percentile(projected, [5, 95])
    middle = (order[:-1] >= lo + 0.2 * (hi - lo)) & (order[1:] <= hi - 0.2 * (hi - lo))
    if not middle.any():
        return None
    gaps = np.diff(order)
    gaps[~middle] = 0
    split = int(np.argmax(gaps))
    if gaps[split] < LEG_GAP_FRACTION * (hi - lo):
        return None
    cut = (order[split] + order[split + 1]) / 2
    legs = [points_2d[projected < cut], points_2d[projected > cut]]
    return legs if all(len(leg) >= MIN_SLICE_POINTS for leg in legs) else None


def _thigh_perimeter(points_2d: np.ndarray) -> Optional[float]:
    legs = _split_legs(points_2d)
    if legs is None:
        return None  # legs not separable; a combined outline would overstate one thigh
    perimeters = [p for p in (_perimeter(leg) for leg in legs) if p is not None]
    return float(np.mean(perimeters)) if perimeters else None


def _perimeter(points_2d: np.ndarray) -> Optional[float]:
    ring = _radial_profile(points_2d)
    if ring is None:
        return None
    return float(np.sum(np.linalg.norm(ring - np.roll(ring, 1, axis=0), axis=1)))


def _width(points_2d: np.ndarray) -> Optional[float]:
    ring = _radial_profile(points_2d)
    if ring is None:
        return None
    centered = ring - ring.mean(axis=0)
    _, _, vt = np.linalg.svd(centered, full_matrices=False)
    projected = centered @ vt[0]
    return float(projected.max() - projected.min())


def compute_measurements(
    points: np.ndarray,
    reference_height_cm: float,
    camera_centers: Optional[np.ndarray] = None,
    view_directions: Optional[np.ndarray] = None,
    up_vectors: Optional[np.ndarray] = None,
) -> Dict:
    if not MIN_HEIGHT_CM <= reference_height_cm <= MAX_HEIGHT_CM:
        raise MeasurementError(f"Height must be between {MIN_HEIGHT_CM} and {MAX_HEIGHT_CM} cm")
    if points is None or len(points) < 50:
        raise MeasurementError("3D model has too few points to measure")

    points = np.asarray(points, dtype=np.float64)
    up = _up_axis(points, up_vectors)
    u, v = _horizontal_basis(up)

    def project(p):
        return p @ up, np.stack([p @ u, p @ v], axis=-1)

    height, planar = project(points)
    focus_2d = None
    if camera_centers is not None and view_directions is not None:
        focus = _rays_focus(np.asarray(camera_centers), np.asarray(view_directions))
        if focus is not None:
            focus_2d = np.array([focus @ u, focus @ v])

    body = points[_isolate_subject(height, planar, focus_2d)]
    body = _remove_outliers(body)
    if len(body) < 50:
        raise MeasurementError("Could not isolate the person in the 3D model")

    height, planar = project(body)
    floor, top = np.percentile(height, 0.5), np.percentile(height, 99.5)
    raw_height = top - floor
    if raw_height <= 0:
        raise MeasurementError("Degenerate 3D model")
    scale = reference_height_cm / raw_height  # model units -> cm
    level = (height - floor) / raw_height

    def slice_at(fraction):
        mask = np.abs(level - fraction) <= SLICE_HALF_THICKNESS
        return planar[mask] * scale

    results: Dict[str, Measurement] = {"height": Measurement(reference_height_cm, "reference")}

    for name, fraction, measure in (("chest", LEVELS["chest"], _perimeter), ("waist", LEVELS["waist"], _perimeter),
                                    ("hip", LEVELS["hip"], _perimeter), ("thigh", LEVELS["thigh"], _thigh_perimeter)):
        perimeter = measure(slice_at(fraction))
        if perimeter is not None:
            results[f"{name}_circumference"] = Measurement(perimeter, "measured")

    for name, fraction in (("shoulder_width", LEVELS["shoulder"]), ("hip_width", LEVELS["hip"])):
        width = _width(slice_at(fraction))
        if width is not None:
            results[name] = Measurement(width, "measured")

    for name, ratio in RATIOS.items():
        results[name] = Measurement(reference_height_cm * ratio, "estimated")

    measured = sum(1 for m in results.values() if m.method == "measured")
    confidence = "high" if measured >= 5 and len(body) > 2000 else "medium" if measured >= 3 else "low"
    logger.info("Computed %d measured values from %d body points", measured, len(body))

    return {
        "unit": "cm",
        "confidence": confidence,
        "body_points": int(len(body)),
        "measurements": {name: m.to_dict() for name, m in results.items()},
    }
