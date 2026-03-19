# (optimizer_api)/Dockerfile
FROM python:3.12-slim-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

ARG DJANGO_SECRET_KEY
ENV DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}

# Set work directory
WORKDIR /app

# Install system dependencies (removed gcc g++ for smaller image)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl libffi-dev libssl-dev gnupg2 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


# Install Python dependencies
COPY requirements.txt .
RUN python -m pip install --upgrade pip==25.2 && \
    pip install --default-timeout=200 --retries 10 --no-cache-dir --progress-bar=off -r requirements.txt    

# Copy project files
COPY . /app

# ----- prepare runtime dirs & permissions while still root -----
RUN mkdir -p /app/staticfiles /app/mediafiles && \
    addgroup --system appgroup && \
    adduser --system --ingroup appgroup --home /app --no-create-home appuser && \
    chown -R appuser:appgroup /app    

USER appuser

# Make entrypoint script executable
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]

# ---- Healthcheck ----
# This expects your Django project to expose GET /healthz returning 200.
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -fsS -o /dev/null http://127.0.0.1:8000/healthz || exit 1

# Use Gunicorn as WSGI server > shifted to docker-compose
# CMD ["gunicorn", "optimizer_api.wsgi:application", "--bind", "0.0.0.0:8000", "--workers=3", "--threads=2", "--timeout=120"]