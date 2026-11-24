import math

import numpy as np
import pytest

from api.modules.measurements import MeasurementError, compute_measurements


def ellipse_perimeter(a, b):
    h = ((a - b) ** 2) / ((a + b) ** 2)
    return math.pi * (a + b) * (1 + 3 * h / (10 + math.sqrt(4 - 3 * h)))


def synthetic_body(scale=0.01, n=40000, seed=1):
    """An elliptic-cylinder 'body' 170 units tall (y down, like COLMAP), plus background clutter."""
    rng = np.random.default_rng(seed)
    y = rng.uniform(0, 170, n)
    theta = rng.uniform(0, 2 * np.pi, n)
    a, b = 16.0, 11.0  # semi-axes in cm
    body = np.stack([a * np.cos(theta), -y, b * np.sin(theta)], axis=1)
    clutter = rng.uniform(-400, 400, (800, 3))
    clutter[:, 1] = rng.uniform(-170, 0, 800)
    clutter = clutter[np.linalg.norm(clutter[:, [0, 2]], axis=1) > 150]
    points = np.vstack([body, clutter]) * scale
    angles = np.linspace(0, 2 * np.pi, 24, endpoint=False)
    centers = np.stack([300 * np.cos(angles), np.full(24, -100.0), 300 * np.sin(angles)], axis=1) * scale
    directions = -centers / np.linalg.norm(centers, axis=1, keepdims=True)
    ups = np.tile([0.0, -1.0, 0.0], (24, 1))
    return points, centers, directions, ups, ellipse_perimeter(a, b), 2 * a


def test_measures_known_shape():
    points, centers, directions, ups, perimeter, width = synthetic_body()
    result = compute_measurements(points, 170, centers, directions, ups)
    m = result["measurements"]
    assert result["unit"] == "cm"
    for key in ("chest_circumference", "waist_circumference", "hip_circumference"):
        assert m[key]["method"] == "measured"
        assert m[key]["value_cm"] == pytest.approx(perimeter, rel=0.05)
    assert m["shoulder_width"]["value_cm"] == pytest.approx(width, rel=0.08)
    assert m["inseam"]["method"] == "estimated"
    assert result["confidence"] == "high"


def test_scale_comes_from_reference_height():
    points, centers, directions, ups, perimeter, _ = synthetic_body(scale=0.0123)
    result = compute_measurements(points, 170, centers, directions, ups)
    assert result["measurements"]["waist_circumference"]["value_cm"] == pytest.approx(perimeter, rel=0.05)


def test_works_without_camera_poses():
    points, *_, perimeter, _ = synthetic_body()
    body_only = points[np.linalg.norm(points[:, [0, 2]], axis=1) < 0.5]
    result = compute_measurements(body_only, 170)
    assert result["measurements"]["hip_circumference"]["value_cm"] == pytest.approx(perimeter, rel=0.05)


def test_rejects_bad_input():
    with pytest.raises(MeasurementError):
        compute_measurements(np.zeros((10, 3)), 170)
    with pytest.raises(MeasurementError):
        compute_measurements(np.random.rand(500, 3), 20)
