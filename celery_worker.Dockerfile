
# --- Dockerfile for Celery Worker ---
# Save as: celery_worker.Dockerfile
FROM python:3.12-slim


WORKDIR /app

COPY requirements.txt ./
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

COPY . .