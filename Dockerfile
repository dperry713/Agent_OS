# --- Stage 1: Builder ---
FROM python:3.11-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /install
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- Stage 2: Final Hardened Runtime ---
FROM python:3.11-slim
LABEL security.policy="strict"
LABEL security.isolation="gvisor-compatible"

# Install runtime dependencies and tini for signal reaping
RUN apt-get update && apt-get install -y --no-install-recommends \
    tini libpq5 curl ca-certificates && rm -rf /var/lib/apt/lists/*

# Create non-root user (UID 10001)
RUN groupadd -g 10001 agentos && \
    useradd -u 10001 -g agentos -s /bin/false -m agentos

WORKDIR /app
COPY --from=builder /install /usr/local
COPY --chown=agentos:agentos . .

# Environment hardening
ENV PYTHONPATH=/app \
    PATH="/usr/local/bin:$PATH" \
    PYTHONUNBUFFERED=1

# Ensure /tmp is the only writeable area for the app
RUN chmod -R 550 /app && \
    chown -R agentos:agentos /app && \
    mkdir -p /tmp/agentos && \
    chown agentos:agentos /tmp/agentos

# Security: Set working directory permissions
USER 10001:10001

# OCI Healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
