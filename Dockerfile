ARG SERVICE=api
ARG TORCH_VARIANT=none

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml .

ARG SERVICE
ARG TORCH_VARIANT
RUN if [ "$TORCH_VARIANT" = "cpu" ]; then pip install torch --index-url https://download.pytorch.org/whl/cpu; fi

RUN pip install --break-system-packages -e ".[$SERVICE]"

COPY src ./src
COPY scripts ./scripts
RUN mkdir -p /app/data

ARG SERVICE
ENV SERVICE="${SERVICE}"

CMD if [ "$SERVICE" = "retrieval" ]; then python -m src.apps.retrieval_service.main; \
    elif [ "$SERVICE" = "worker" ]; then python -m src.apps.worker.main; \
    elif [ "$SERVICE" = "init" ]; then python scripts/init-db.py; \
    elif [ "$SERVICE" = "api" ]; then uvicorn src.apps.public_api.main:app --host 0.0.0.0 --port 8000; \
    fi
