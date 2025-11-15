FROM python:3.10-slim

WORKDIR /app

# Install system dependencies needed for Google Cloud client
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc build-essential \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire package folder
COPY SD_Accounting_Tool/ /app/SD_Accounting_Tool/

ENV PYTHONPATH=/app

# Use gunicorn to serve the package app
CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app", "--timeout", "120", "--workers", "2"]