"""
Main indexer script.

Reads eshop_files.yaml, chunks each file, generates embeddings,
and inserts the chunks into a Qdrant collection.

Run as a build-time job — after this completes, the agent can query the collection.
"""
import os
import sys
import time
from pathlib import Path
from typing import Iterable

import yaml
from tqdm import tqdm
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, OptimizersConfigDiff,
)

from chunking import chunk_file, Chunk


# ----- Configuration -----

QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
COLLECTION = os.getenv("QDRANT_COLLECTION", "eshop_code")
SNAPSHOT_PATH = Path(os.getenv("SNAPSHOT_PATH", "/snapshot"))
MANIFEST_PATH = Path("eshop_files.yaml")
PROVIDER = os.getenv("EMBEDDING_PROVIDER", "local").lower()  # "openai" | "local"
MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


# ----- Embedding providers -----

def get_embedder():
    """Return a callable that takes a list of strings and returns a list of vectors."""
    if PROVIDER == "openai":
        if not OPENAI_API_KEY:
            raise RuntimeError("EMBEDDING_PROVIDER=openai but OPENAI_API_KEY is not set")
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        model = os.getenv("EMBEDDING_MODEL_OPENAI", "text-embedding-3-small")

        def embed(texts: list[str]) -> list[list[float]]:
            resp = client.embeddings.create(model=model, input=texts)
            return [d.embedding for d in resp.data]

        # text-embedding-3-small has dimension 1536
        embed.dim = 1536
        return embed

    # Local fallback
    from sentence_transformers import SentenceTransformer
    print(f"[indexer] Loading local model: {MODEL}")
    st_model = SentenceTransformer(MODEL)

    def embed(texts: list[str]) -> list[list[float]]:
        return st_model.encode(texts, show_progress_bar=False, convert_to_numpy=True).tolist()

    embed.dim = st_model.get_sentence_embedding_dimension()
    return embed


# ----- Qdrant setup -----

def ensure_collection(client: QdrantClient, dim: int):
    """Create the collection if it doesn't exist."""
    collections = client.get_collections().collections
    names = [c.name for c in collections]
    if COLLECTION in names:
        print(f"[indexer] Collection '{COLLECTION}' already exists. Recreating.")
        client.delete_collection(COLLECTION)

    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        optimizers_config=OptimizersConfigDiff(indexing_threshold=10),
    )
    print(f"[indexer] Collection '{COLLECTION}' created with dim={dim}")


def wait_for_qdrant(timeout_seconds: int = 90):
    """Wait until Qdrant is reachable before indexing."""
    deadline = time.time() + timeout_seconds
    last_error = None

    while time.time() < deadline:
        try:
            client = QdrantClient(url=QDRANT_URL)
            client.get_collections()
            print("[indexer] Qdrant is reachable")
            return client
        except Exception as exc:
            last_error = exc
            print(f"[indexer] Waiting for Qdrant at {QDRANT_URL}...")
            time.sleep(3)

    raise RuntimeError(f"Qdrant did not become ready within {timeout_seconds}s: {last_error}")


# ----- Manifest loading -----

def load_manifest() -> dict:
    with MANIFEST_PATH.open() as f:
        return yaml.safe_load(f)


def iter_files(manifest: dict) -> Iterable[tuple[Path, dict]]:
    """Yield (file_path, metadata) for each entry in the manifest."""
    for entry in manifest.get("files", []):
        rel = entry["path"]
        full = SNAPSHOT_PATH / rel
        if not full.exists():
            print(f"[indexer] WARNING: file not found in snapshot: {full}")
            continue
        yield full, entry

    for entry in manifest.get("docs", []):
        rel = entry["path"]
        full = SNAPSHOT_PATH / rel
        if not full.exists():
            print(f"[indexer] WARNING: doc not found in snapshot: {full}")
            continue
        # Skip binary files (images, etc.)
        if Path(rel).suffix.lower() in (".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico"):
            print(f"[indexer] Skipping binary file: {rel}")
            continue
        yield full, entry


# ----- Main pipeline -----

def main():
    print(f"[indexer] Starting eShop indexer")
    print(f"[indexer] Snapshot path: {SNAPSHOT_PATH}")
    print(f"[indexer] Qdrant URL: {QDRANT_URL}")
    print(f"[indexer] Embedding provider: {PROVIDER}")

    if not SNAPSHOT_PATH.exists():
        print(f"[indexer] FATAL: snapshot path does not exist: {SNAPSHOT_PATH}")
        sys.exit(1)

    manifest = load_manifest()
    embedder = get_embedder()
    client = wait_for_qdrant()
    ensure_collection(client, embedder.dim)

    point_id = 0
    points_buffer: list[PointStruct] = []

    for file_path, entry in tqdm(list(iter_files(manifest)), desc="Indexing files"):
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"[indexer] Failed to read {file_path}: {e}")
            continue

        chunks: list[Chunk] = chunk_file(file_path, content)
        if not chunks:
            continue

        texts = [c.text for c in chunks]
        vectors = embedder(texts)

        for chunk, vector in zip(chunks, vectors):
            payload = {
                "file_path": str(file_path.relative_to(SNAPSHOT_PATH)),
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "section": chunk.section,
                "service": entry.get("service"),
                "role": entry.get("role"),
                "language": entry.get("language"),
                "scenarios": entry.get("relevant_to_scenarios", []),
                "description": entry.get("description"),
                "text": chunk.text,
            }
            points_buffer.append(PointStruct(id=point_id, vector=vector, payload=payload))
            point_id += 1

        # Flush buffer in batches
        if len(points_buffer) >= 100:
            client.upsert(collection_name=COLLECTION, points=points_buffer)
            points_buffer = []

    # Final flush
    if points_buffer:
        client.upsert(collection_name=COLLECTION, points=points_buffer)

    print(f"[indexer] Done. Total points indexed: {point_id}")


if __name__ == "__main__":
    main()
