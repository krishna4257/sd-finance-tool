FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends gcc

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy full project folder
COPY SD_Accounting_Tool/ /app/SD_Accounting_Tool/
COPY cloudbuild.yaml .
COPY config.py .

# Enable package-style imports
ENV PYTHONPATH=/app

# Start server
CMD ["gunicorn", "-b", "0.0.0.0:8080", "SD_Accounting_Tool.app:app"]