FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_ENV=production \
    DATA_DIR=/app/data \
    PORT=5000 \
    MEDIAPIPE_DISABLE_GPU=1 \
    HOME=/home/measulor

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libgl1 libglib2.0-0 libgomp1 libxcb1 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .

RUN pip install -r requirements.txt \
    && python - <<'PY'
import numpy as np
import mediapipe as mp
print("mediapipe", mp.__version__)
pose = mp.solutions.pose.Pose(
    static_image_mode=True,
    model_complexity=0,
    enable_segmentation=False,
    min_detection_confidence=0.3,
)
blank = np.zeros((256, 192, 3), dtype=np.uint8)
pose.process(blank)
pose.close()
print("pose models warmed")
PY

COPY api ./api
COPY main.py gunicorn.conf.py ./

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN useradd --create-home --uid 10001 measulor \
    && mkdir -p /app/data /home/measulor \
    && chown -R measulor:measulor /app/data /home/measulor \
    && chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=45s CMD curl -fsS http://localhost:${PORT}/health || exit 1
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["gunicorn", "-c", "gunicorn.conf.py", "api.index:app"]
