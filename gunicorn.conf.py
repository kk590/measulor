import os

bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"
# A single worker process owns the background job queue; threads serve HTTP requests.
workers = 1
threads = int(os.environ.get("GUNICORN_THREADS", "8"))
timeout = 120
graceful_timeout = 30
accesslog = "-"
errorlog = "-"
