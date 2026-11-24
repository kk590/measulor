"""Module 2 - 3D model: multi-view sparse reconstruction with COLMAP (pycolmap)."""

import logging
import os
import shutil
from dataclasses import dataclass
from typing import List

import cv2
import numpy as np

try:
    import pycolmap
except ImportError:  # pragma: no cover - depends on deployment image
    pycolmap = None

logger = logging.getLogger(__name__)

MIN_REGISTERED_IMAGES = 5
MIN_POINTS = 200


class ReconstructionError(RuntimeError):
    """Raised when a usable 3D model cannot be built from the frames."""


@dataclass
class Model3D:
    points: np.ndarray
    colors: np.ndarray
    ply_path: str
    registered_images: int
    total_images: int
    mean_reprojection_error: float
    camera_centers: np.ndarray
    view_directions: np.ndarray
    up_vectors: np.ndarray

    def stats(self) -> dict:
        return {
            "points": int(len(self.points)),
            "registered_frames": self.registered_images,
            "total_frames": self.total_images,
            "mean_reprojection_error_px": round(self.mean_reprojection_error, 3),
        }


def reconstruct(frames: List[np.ndarray], work_dir: str) -> Model3D:
    """Build a sparse point cloud from ordered video frames and write it to work_dir/model.ply."""
    if pycolmap is None:
        raise ReconstructionError("pycolmap is not installed on this server")

    image_dir = os.path.join(work_dir, "images")
    sparse_dir = os.path.join(work_dir, "sparse")
    db_path = os.path.join(work_dir, "database.db")
    os.makedirs(image_dir, exist_ok=True)
    os.makedirs(sparse_dir, exist_ok=True)

    for i, frame in enumerate(frames):
        cv2.imwrite(os.path.join(image_dir, f"frame_{i:04d}.jpg"), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])

    try:
        # All frames come from one camera, so share intrinsics across images.
        pycolmap.extract_features(db_path, image_dir, camera_mode=pycolmap.CameraMode.SINGLE)
        pycolmap.match_sequential(db_path)
        maps = pycolmap.incremental_mapping(db_path, image_dir, sparse_dir)
    except Exception as exc:
        logger.exception("COLMAP failed")
        raise ReconstructionError(f"3D reconstruction failed: {exc}") from exc
    finally:
        shutil.rmtree(image_dir, ignore_errors=True)
        if os.path.exists(db_path):
            os.remove(db_path)

    if not maps:
        raise ReconstructionError(
            "Could not reconstruct a 3D model. Walk slowly around the person with steady overlap between views."
        )

    model = max(maps.values(), key=lambda rec: rec.num_points3D())
    registered = model.num_reg_images()
    if registered < MIN_REGISTERED_IMAGES or model.num_points3D() < MIN_POINTS:
        raise ReconstructionError(
            f"3D model is too sparse ({registered} frames registered, {model.num_points3D()} points). "
            "Use a textured background, good lighting and a slower camera motion."
        )

    centers, directions, ups = _camera_geometry(model)
    points = np.array([p.xyz for p in model.points3D.values()], dtype=np.float64)
    colors = np.array([p.color for p in model.points3D.values()], dtype=np.uint8)
    ply_path = os.path.join(work_dir, "model.ply")
    model.export_PLY(ply_path)
    shutil.rmtree(sparse_dir, ignore_errors=True)

    return Model3D(
        points=points,
        colors=colors,
        ply_path=ply_path,
        registered_images=registered,
        total_images=len(frames),
        mean_reprojection_error=float(model.compute_mean_reprojection_error()),
        camera_centers=centers,
        view_directions=directions,
        up_vectors=ups,
    )


def _camera_geometry(model):
    centers, directions, ups = [], [], []
    for image in model.images.values():
        if not image.has_pose:
            continue
        pose = image.cam_from_world() if callable(image.cam_from_world) else image.cam_from_world
        rotation = np.asarray(pose.rotation.matrix())
        centers.append(np.asarray(image.projection_center()))
        directions.append(rotation.T @ np.array([0.0, 0.0, 1.0]))
        # Image y points down, so camera "up" in world coordinates is -y.
        ups.append(rotation.T @ np.array([0.0, -1.0, 0.0]))
    return np.array(centers), np.array(directions), np.array(ups)
