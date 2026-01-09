#!/bin/bash

# Install dependencies from requirements-full.txt
pip install -r requirements-full.txt

# Start gunicorn server for the measurement API
gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 2 api.measure:app
