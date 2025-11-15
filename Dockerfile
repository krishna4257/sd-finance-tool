FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for google-cloud-storage
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY config.py .
COPY gcs_utils.py .
COPY database_manager.py .

# Copy templates and static assets
COPY templates/ templates/
COPY static/ static/

# Expose port
EXPOSE 8080

# Start app with gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app"]