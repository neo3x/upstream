# Reuse the model weights already baked into the indexer image
FROM upstream-indexer:latest AS model-cache

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the cached HuggingFace model from the indexer image (avoids re-download)
COPY --from=model-cache /root/.cache/huggingface /root/.cache/huggingface

COPY app/ ./app/

RUN mkdir -p /app/data/checkpoints
VOLUME ["/app/data/checkpoints"]

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
