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
MAX_DIMENSION = 1600
MIN_SIDE = 200


class PhotoError(ValueError):
    """Raised when photos cannot be accepted or processed."""


def save_uploads(files: List[FileStorage], upload_dir: str) -> List[str]:
    """Validate and store one or more photo uploads."""
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
    """Decode photos, reject tiny/corrupt ones, resize for speed."""
    images = []
    for path in paths:
        image = cv2.imread(path)
        if image is None:
            raise PhotoError(f"Could not decode image: {os.path.basename(path)}")
        h, w = image.shape[:2]
        if min(h, w) < MIN_SIDE:
            raise PhotoError("Photo is too small. Use at least 200px on the short side")
        scale = MAX_DIMENSION / float(max(h, w))
        if scale < 1.0:
            image = cv2.resize(
                image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA
            )
        images.append(image)
    logger.info("Loaded %d photo(s)", len(images))
    return images
