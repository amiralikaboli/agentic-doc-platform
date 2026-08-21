ARG BASE_IMAGE=python:3.12-slim
FROM ${BASE_IMAGE} as builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    protobuf-compiler \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy pyproject.toml early for dependency layer caching
COPY pyproject.toml .
RUN pip install ".[build]"

# Define service type (api, retrieval, worker, or init)
ARG SERVICE=api

# Install dependencies with extended timeout
RUN pip install ".[$SERVICE]"

# Copy proto and scripts, generate gRPC code
COPY proto ./proto
COPY scripts ./scripts
RUN bash scripts/gen_proto.sh

# Copy source code
COPY src ./src

# Create data directory
RUN mkdir -p /app/data

# Final runtime stage — minimal footprint
ARG BASE_IMAGE=python:3.12-slim
FROM ${BASE_IMAGE}

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

ARG SERVICE=api
ENV SERVICE="${SERVICE}"

# Minimal runtime deps only (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy entire build output from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app

# Service-specific entrypoints
CMD if [ "$SERVICE" = "retrieval" ]; then \
      python -m src.apps.retrieval_service.main; \
    elif [ "$SERVICE" = "worker" ]; then \
      python -m src.apps.worker.main; \
    elif [ "$SERVICE" = "init" ]; then \
      python scripts/init-db.py; \
    else \
      uvicorn src.apps.public_api.main:app --host 0.0.0.0 --port 8000 --reload; \
    fi
