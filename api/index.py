"""WSGI entry point: `gunicorn api.index:app`."""

from . import create_app

app = create_app()
