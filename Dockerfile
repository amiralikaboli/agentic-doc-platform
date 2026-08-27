ARG ENVIRONMENT=local
ARG SERVICE=api
ARG GPU_SERVICE=false

# Select base image: CUDA only for retrieval/worker in GPU environment
FROM python:3.12-slim AS base-cpu
FROM nvidia/cuda:13.3.1-runtime-ubuntu24.04 AS base-gpu
FROM base-$( if [ "$ENVIRONMENT" = "gpu" ] && [ "$GPU_SERVICE" = "true" ]; then echo gpu; else echo cpu; fi ) as builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install Python and build tools (needed for GPU base image)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.12 \
    python3-pip \
    build-essential \
    libpq-dev \
    protobuf-compiler \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy pyproject.toml early for dependency layer caching
COPY pyproject.toml .
RUN pip install ".[build]"

# Install torch based on environment:
# - local/ci: install CPU version (smaller wheels for dev)
# - gpu: skip (CUDA already in base image)
ARG ENVIRONMENT=local
ARG GPU_SERVICE=false
RUN if ([ "$SERVICE" = "retrieval" ] || [ "$SERVICE" = "worker" ]) && \
       ([ "$ENVIRONMENT" = "local" ] || [ "$ENVIRONMENT" = "ci" ]); then \
      echo "Installing torch CPU for $SERVICE in $ENVIRONMENT environment..."; \
      pip install torch --index-url https://download.pytorch.org/whl/cpu; \
    fi

# Install service-specific dependencies
RUN pip install -e ".[$SERVICE]"

# Copy proto and scripts, generate gRPC code
COPY proto ./proto
COPY scripts ./scripts
RUN bash scripts/gen_proto.sh

# Copy source code
COPY src ./src

# Create data directory
RUN mkdir -p /app/data

# Final runtime stage — minimal footprint
ARG ENVIRONMENT=local
ARG SERVICE=api
ARG GPU_SERVICE=false

FROM python:3.12-slim AS runtime-cpu
FROM nvidia/cuda:13.3.1-runtime-ubuntu24.04 AS runtime-gpu
FROM runtime-$( if [ "$ENVIRONMENT" = "gpu" ] && [ "$GPU_SERVICE" = "true" ]; then echo gpu; else echo cpu; fi )

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

ARG SERVICE=api
ENV SERVICE="${SERVICE}"

# Install Python and minimal runtime deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.12 \
    python3-pip \
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
