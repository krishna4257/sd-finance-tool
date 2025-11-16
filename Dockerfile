# Use Python 3.10+
FROM python:3.10-slim

# Install pip dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Cloud Run uses port 8080
ENV PORT 8080

# Start Flask using gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app"]