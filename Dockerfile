FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN mkdir -p /app/data

# Install CPU-only PyTorch first via custom index
RUN pip install --no-cache-dir 'torch>=2.0,<3.0' --index-url https://download.pytorch.org/whl/cpu

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY src ./src

CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]