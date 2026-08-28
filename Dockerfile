ARG SERVICE=api
ARG BASE_IMAGE=python:3.12-slim
ARG TORCH_VARIANT=none

FROM ${BASE_IMAGE} AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

ARG BASE_IMAGE
RUN case "$BASE_IMAGE" in \
      *python*) apt-get update && \
                apt-get install -y --no-install-recommends build-essential libpq-dev protobuf-compiler && \
                rm -rf /var/lib/apt/lists/* ;; \
      *) apt-get update && \
         apt-get install -y --no-install-recommends python3.12 python3-pip build-essential libpq-dev protobuf-compiler && \
         rm -rf /var/lib/apt/lists/* ;; \
    esac

WORKDIR /app
COPY pyproject.toml .
RUN pip install ".[build]"

ARG SERVICE
ARG TORCH_VARIANT
RUN if [ "$TORCH_VARIANT" = "cpu" ]; then pip install torch --index-url https://download.pytorch.org/whl/cpu; fi

RUN pip install -e ".[$SERVICE]"

COPY proto ./proto
COPY scripts ./scripts
RUN bash scripts/gen_proto.sh
COPY src ./src
RUN mkdir -p /app/data

ARG BASE_IMAGE
FROM ${BASE_IMAGE} AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
ARG SERVICE
ENV SERVICE="${SERVICE}"

ARG BASE_IMAGE
RUN case "$BASE_IMAGE" in \
      *python*) apt-get update && \
                apt-get install -y --no-install-recommends build-essential libpq-dev protobuf-compiler && \
                rm -rf /var/lib/apt/lists/* ;; \
      *) apt-get update && \
         apt-get install -y --no-install-recommends python3.12 python3-pip build-essential libpq-dev protobuf-compiler && \
         rm -rf /var/lib/apt/lists/* ;; \
    esac

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app

CMD if [ "$SERVICE" = "retrieval" ]; then python -m src.apps.retrieval_service.main; \
    elif [ "$SERVICE" = "worker" ]; then python -m src.apps.worker.main; \
    elif [ "$SERVICE" = "init" ]; then python scripts/init-db.py; \
    elif [ "$SERVICE" = "api" ]; then uvicorn src.apps.public_api.main:app --host 0.0.0.0 --port 8000; \
    fi