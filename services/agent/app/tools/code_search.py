"""Semantic search tool over the indexed eShop snapshot."""
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from ..config import settings


_model = None
_client = None


def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.embedding_model)
    return _model


def _get_client():
    global _client
    if _client is None:
        _client = QdrantClient(url=settings.qdrant_url)
    return _client


def search_eshop_code(query: str, top_k: int = 5, service_filter: str | None = None) -> list[dict]:
    """Search the indexed eShop code semantically.

    Returns a list of payloads with file_path, line range, service, role, text.
    """
    model = _get_model()
    client = _get_client()
    vector = model.encode(query).tolist()

    filter_obj = None
    if service_filter:
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        filter_obj = Filter(
            must=[FieldCondition(key="service", match=MatchValue(value=service_filter))]
        )

    results = client.search(
        collection_name=settings.qdrant_collection,
        query_vector=vector,
        limit=top_k,
        query_filter=filter_obj,
    )
    return [{**r.payload, "score": r.score} for r in results]
