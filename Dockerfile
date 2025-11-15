FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire app (VERY IMPORTANT)
COPY . /app

# Expose port
EXPOSE 8080

# Run gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app"]