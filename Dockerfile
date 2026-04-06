# ── Stage 1: dependency builder ───────────────────────────────────────────
# Installs Python packages into an isolated prefix so the final image
# only copies compiled wheels — no build tools (gcc, pip cache) in production.
FROM python:3.11-slim AS builder

WORKDIR /build

# System build deps needed by thrift (C extension) and reportlab (libjpeg)
RUN apt-get update && apt-get install -y --no-install-recommends \
	gcc \
	libjpeg-dev \
	zlib1g-dev \
	&& rm -rf /var/lib/apt/lists/*

COPY requirements-prod.txt .
RUN pip install --upgrade pip \
	&& pip install --prefix=/install --no-cache-dir -r requirements-prod.txt


# ── Stage 2: production image ─────────────────────────────────────────────
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	FLASK_ENV=production

WORKDIR /app

# Runtime deps only (libjpeg needed by reportlab at runtime)
RUN apt-get update && apt-get install -y --no-install-recommends \
	libjpeg62-turbo \
	&& rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder stage
COPY --from=builder /install /usr/local

# Copy application source
COPY configs/   ./configs/
COPY common/    ./common/
COPY webapp/    ./webapp/

# Create data/auth directory for users.db — volume will be mounted here
RUN mkdir -p /app/data/auth

# Run as non-root user for security
RUN useradd --create-home --shell /bin/bash appuser \
	&& chown -R appuser:appuser /app
USER appuser

EXPOSE 5001

# Gunicorn for production; fall back to Flask dev server if gunicorn not available.
# The pipeline (Spark/HBase) runs on the host — this container only serves the webapp.
CMD ["python3", "-m", "webapp.app"]