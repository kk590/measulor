"""Module 1 - Photos: upload validation and image loading."""

import logging
import os
import uuid
from typing import List

import cv2
import numpy as np
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "bmp"}
MIN_PHOTOS = 1
MAX_PHOTOS = 8
MAX_DIMENSION = 1280
MIN_SIDE = 160


class PhotoError(ValueError):
    """Raised when photos cannot be accepted or processed."""


def save_uploads(files: List[FileStorage], upload_dir: str) -> List[str]:
    if not files:
        raise PhotoError("No photo files provided")
    usable = [f for f in files if f and f.filename]
    if not usable:
        raise PhotoError("No photo files provided")
    if len(usable) > MAX_PHOTOS:
        raise PhotoError(f"Too many photos. Maximum is {MAX_PHOTOS}")
    os.makedirs(upload_dir, exist_ok=True)
    paths = []
    for file in usable:
        filename = secure_filename(file.filename or "")
        if "." not in filename:
            raise PhotoError("Missing file extension")
        extension = filename.rsplit(".", 1)[1].lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise PhotoError(
                f"Unsupported format '{extension}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )
        path = os.path.join(upload_dir, f"{uuid.uuid4().hex}.{extension}")
        file.save(path)
        if os.path.getsize(path) == 0:
            os.remove(path)
            raise PhotoError("Uploaded file is empty")
        paths.append(path)
    return paths


def load_images(paths: List[str]) -> List[np.ndarray]:
    images = []
    for path in paths:
        image = cv2.imread(path, cv2.IMREAD_COLOR)
        if image is None:
            data = np.fromfile(path, dtype=np.uint8)
            image = cv2.imdecode(data, cv2.IMREAD_COLOR)
        if image is None:
            raise PhotoError(f"Could not decode image: {os.path.basename(path)}")
        if image.dtype != np.uint8:
            image = np.clip(image, 0, 255).astype(np.uint8)
        if image.ndim == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        elif image.ndim == 3 and image.shape[2] == 4:
            image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
        h, w = image.shape[:2]
        if min(h, w) < MIN_SIDE:
            raise PhotoError("Photo is too small. Use at least 160px on the short side")
        scale = MAX_DIMENSION / float(max(h, w))
        if scale < 1.0:
            image = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        if not image.flags["C_CONTIGUOUS"]:
            image = np.ascontiguousarray(image)
        images.append(image)
    logger.info("Loaded %d photo(s)", len(images))
    return images
