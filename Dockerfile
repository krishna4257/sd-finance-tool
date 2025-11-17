# Dockerfile - optimized for Cloud Run
FROM python:3.10-slim

# Install system deps (if you need: ffmpeg, libmagic, etc add here)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# copy only requirements first (better caching)
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy app source
COPY . .

# Use PORT env var provided by Cloud Run (default 8080)
ENV PORT=8080
# Production command — assumes app.py defines `app` (Flask instance)
CMD exec gunicorn --bind ":$PORT" --workers 4 --threads 8 --timeout 120 app:app