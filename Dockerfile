FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for Google Cloud client
RUN apt-get update && apt-get install -y --no-install-recommends gcc

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything into the container
COPY . /app/

# Ensure Python can import modules from /app
ENV PYTHONPATH=/app

# Start Gunicorn server
CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app"]