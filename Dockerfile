FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y build-essential gcc

RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    unixodbc-dev \
    libpq-dev \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . /app

ENV PORT=8080
ENV GCS_BUCKET=sd-finance-db

EXPOSE 8080

CMD exec gunicorn --bind :$PORT --workers 2 --threads 4 app:app