import io

import cv2
import numpy as np
import pytest
from werkzeug.datastructures import FileStorage

from api.modules import video


def write_video(path, seconds=4, fps=10, blurry=False):
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (320, 240))
    rng = np.random.default_rng(0)
    for _ in range(seconds * fps):
        frame = rng.integers(0, 255, (240, 320, 3), dtype=np.uint8)
        if blurry:
            frame = np.full((240, 320, 3), 128, dtype=np.uint8)
        writer.write(frame)
    writer.release()
    return str(path)


def test_probe_and_extract(tmp_path):
    path = write_video(tmp_path / "ok.mp4")
    info = video.probe(path, max_duration_seconds=60)
    assert 3.5 < info.duration < 4.5
    frames = video.extract_frames(path, info, max_frames=15, max_dimension=160)
    assert 10 <= len(frames) <= 15
    assert max(frames[0].shape[:2]) == 160


def test_rejects_blurry_video(tmp_path):
    path = write_video(tmp_path / "flat.mp4", blurry=True)
    info = video.probe(path, max_duration_seconds=60)
    with pytest.raises(video.VideoError, match="usable frames"):
        video.extract_frames(path, info, max_frames=15, max_dimension=320)


def test_rejects_long_and_short_videos(tmp_path):
    path = write_video(tmp_path / "ok.mp4")
    with pytest.raises(video.VideoError, match="too long"):
        video.probe(path, max_duration_seconds=2)
    short = write_video(tmp_path / "short.mp4", seconds=1)
    with pytest.raises(video.VideoError, match="too short"):
        video.probe(short, max_duration_seconds=60)


def test_save_upload_validates_extension(tmp_path):
    with pytest.raises(video.VideoError):
        video.save_upload(FileStorage(io.BytesIO(b"x"), "evil.sh"), str(tmp_path))
    saved = video.save_upload(FileStorage(io.BytesIO(b"x"), "../../clip.MP4"), str(tmp_path))
    assert saved.startswith(str(tmp_path)) and saved.endswith(".mp4")
