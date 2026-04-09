FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git \
    && rm -rf /var/lib/apt/lists/*

COPY indexer/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the local embedding model so it's baked into the image
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY indexer/index_eshop.py indexer/chunking.py ./
COPY indexer/eshop_files.yaml ./
COPY eshop_snapshot/ /snapshot/

ENV QDRANT_URL=http://qdrant:6333
ENV QDRANT_COLLECTION=eshop_code
ENV EMBEDDING_PROVIDER=local
ENV EMBEDDING_MODEL=all-MiniLM-L6-v2
ENV SNAPSHOT_PATH=/snapshot

CMD ["python", "index_eshop.py"]
