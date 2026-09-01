ARG SERVICE=api
ARG BASE_IMAGE=python:3.12-slim
ARG TORCH_VARIANT=none

FROM ${BASE_IMAGE}

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

ARG BASE_IMAGE
RUN case "$BASE_IMAGE" in \
      *python*) apt-get update && \
                apt-get install -y --no-install-recommends build-essential libpq-dev && \
                rm -rf /var/lib/apt/lists/* ;; \
      *) apt-get update && \
         apt-get install -y --no-install-recommends python3.12-full python3-pip build-essential libpq-dev && \
         rm -rf /var/lib/apt/lists/* ;; \
    esac

WORKDIR /app
COPY pyproject.toml .

ARG SERVICE
ARG TORCH_VARIANT
RUN if [ "$TORCH_VARIANT" = "cpu" ]; then pip install torch --index-url https://download.pytorch.org/whl/cpu; fi

RUN pip install -e ".[$SERVICE]"

COPY src ./src
RUN mkdir -p /app/data

ARG SERVICE
ENV SERVICE="${SERVICE}"

CMD if [ "$SERVICE" = "retrieval" ]; then python -m src.apps.retrieval_service.main; \
    elif [ "$SERVICE" = "worker" ]; then python -m src.apps.worker.main; \
    elif [ "$SERVICE" = "init" ]; then python scripts/init-db.py; \
    elif [ "$SERVICE" = "api" ]; then uvicorn src.apps.public_api.main:app --host 0.0.0.0 --port 8000; \
    fi
