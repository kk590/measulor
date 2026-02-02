# Dockerfile for Flask API on Render
FROM python:3.10-slim-bookworm

# Install system dependencies for OpenCV headless and other packages
RUN apt-get update && apt-get install -y libsm6 libxrender1 libglib2.0-0 libgomp1 libgl1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the API code (not the GUI)
COPY api ./api
COPY railway_app.py .

# Expose port
EXPOSE 5000

ENV FLASK_APP=api/index.py
ENV FLASK_ENV=production

# Run Flask app
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=5000"]
