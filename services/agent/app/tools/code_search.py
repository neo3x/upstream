"""Semantic search tool over the indexed eShop snapshot.

Uses Qdrant when available and falls back to lexical search over the curated
snapshot when local vector infrastructure is unavailable.
"""
import re
from pathlib import Path

from ..config import settings

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover - dependency may be unavailable in minimal local runs
    SentenceTransformer = None

try:
    from qdrant_client import QdrantClient
except Exception:  # pragma: no cover - dependency may be unavailable in minimal local runs
    QdrantClient = None

_model = None
_client = None
_semantic_search_available = True
def _discover_repo_root() -> Path:
    resolved = Path(__file__).resolve()
    parents = [resolved.parent, *resolved.parents]

    for parent in parents:
        if (parent / "eshop_snapshot").exists():
            return parent

    try:
        return resolved.parents[4]
    except IndexError:
        return resolved.parents[len(resolved.parents) - 1]


REPO_ROOT = _discover_repo_root()
SNAPSHOT_ROOT = REPO_ROOT / "eshop_snapshot"
TEXT_EXTENSIONS = {".cs", ".md", ".txt", ".json", ".yaml", ".yml"}
STOPWORDS = {
    "the", "and", "for", "that", "with", "from", "this", "what", "when", "into",
    "logs", "log", "show", "shows", "reporter", "service", "services", "errors",
    "error", "code", "codes", "summary", "started", "about", "their", "still",
    "have", "has", "been", "were", "dont", "don't", "going", "attached", "issue",
}


def _get_model():
    global _model
    if _model is None:
        if SentenceTransformer is None:
            raise RuntimeError("sentence-transformers is not available")
        _model = SentenceTransformer(settings.embedding_model)
    return _model


def _get_client():
    global _client
    if _client is None:
        if QdrantClient is None:
            raise RuntimeError("qdrant-client is not available")
        _client = QdrantClient(url=settings.qdrant_url)
    return _client


def search_eshop_code(query: str, top_k: int = 5, service_filter: str | None = None) -> list[dict]:
    """Search the indexed eShop code semantically.

    Returns a list of payloads with file_path, line range, service, role, text.
    """
    global _semantic_search_available
    if not _semantic_search_available:
        return _fallback_search(query=query, top_k=top_k, service_filter=service_filter)

    try:
        client = _get_client()
        if not _qdrant_collection_exists(client):
            _semantic_search_available = False
            return _fallback_search(query=query, top_k=top_k, service_filter=service_filter)

        model = _get_model()
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
    except Exception:
        _semantic_search_available = False
        return _fallback_search(query=query, top_k=top_k, service_filter=service_filter)


def _fallback_search(query: str, top_k: int = 5, service_filter: str | None = None) -> list[dict]:
    keywords = _extract_keywords(query)
    results: list[dict] = []

    if not SNAPSHOT_ROOT.exists():
        return results

    for file_path in SNAPSHOT_ROOT.rglob("*"):
        if not file_path.is_file() or file_path.suffix.lower() not in TEXT_EXTENSIONS:
            continue

        snapshot_relative = file_path.relative_to(SNAPSHOT_ROOT)
        if len(snapshot_relative.parts) == 1 and file_path.name.lower() == "readme.md":
            continue

        relative_path = file_path.relative_to(REPO_ROOT).as_posix()
        service_name = snapshot_relative.parts[0]
        if service_filter and service_filter.lower() not in service_name.lower():
            continue

        text = file_path.read_text(encoding="utf-8", errors="ignore")
        score, match_line = _score_file(relative_path, text, keywords)
        if score <= 0:
            continue

        lines = text.splitlines()
        start_line = max(1, match_line - 2)
        end_line = min(len(lines), match_line + 8)
        excerpt = "\n".join(lines[start_line - 1:end_line])

        results.append({
            "file_path": relative_path,
            "start_line": start_line,
            "end_line": end_line,
            "service": service_name,
            "role": "lexical_fallback",
            "text": excerpt,
            "score": float(score),
        })

    return sorted(results, key=lambda item: item["score"], reverse=True)[:top_k]


def _extract_keywords(query: str) -> list[str]:
    raw_tokens = re.findall(r"[A-Za-z0-9_.:/-]+", query.lower())
    keywords: list[str] = []
    for token in raw_tokens:
        stripped = token.strip(".,:;!?()[]{}\"'")
        if not stripped or stripped in STOPWORDS:
            continue
        if len(stripped) < 3 and not stripped.isdigit():
            continue
        keywords.append(stripped)

    extras = []
    joined = " ".join(keywords)
    if "identity" in joined:
        extras.extend(["identity.api", "userinfo", "authentication"])
    if "ordering" in joined:
        extras.extend(["ordering.api", "order"])
    if "payment" in joined or "pending" in joined:
        extras.extend(["paymentprocessor", "orderpaymentsucceededintegrationevent"])
    if "event" in joined or "published" in joined or "rabbitmq" in joined:
        extras.extend(["eventbus", "eventbusrabbitmq", "rabbitmq", "integrationevent"])
    if any(token in joined for token in ("ack", "acknowledgment", "acknowledgement", "consumer", "consumed", "handler")):
        extras.extend(["processevent", "basicack", "handle", "subscription"])
    if "401" in keywords:
        extras.extend(["unauthorized", "userinfo", "identityservice"])
    if "token" in joined or "auth" in joined or "identity" in joined:
        extras.extend(["identityservice", "adddefaultauthentication", "userinfo"])

    return list(dict.fromkeys(keywords + extras))


def _score_file(relative_path: str, text: str, keywords: list[str]) -> tuple[float, int]:
    lower_path = relative_path.lower()
    lower_text = text.lower()
    score = 0.0
    first_line = 1

    for keyword in keywords:
        path_hits = lower_path.count(keyword)
        text_hits = lower_text.count(keyword)
        if not path_hits and not text_hits:
            continue

        score += path_hits * 5
        score += min(text_hits, 6)

        line_number = _find_line_number(lower_text, keyword)
        if line_number and first_line == 1:
            first_line = line_number

    if any(token in lower_path for token in ("eventbus", "rabbitmq")) and any(
        token in keywords
        for token in (
            "eventbus",
            "eventbusrabbitmq",
            "rabbitmq",
            "integrationevent",
            "published",
            "consumer",
            "acknowledgment",
            "acknowledgement",
            "basicack",
            "processevent",
        )
    ):
        score += 6

    if any(token in lower_path for token in ("identity.api", "servicedefaults", "extensions.cs")) and any(
        token in keywords
        for token in (
            "identity",
            "identity.api",
            "401",
            "unauthorized",
            "authentication",
            "userinfo",
            "token",
            "identityservice",
            "adddefaultauthentication",
        )
    ):
        score += 4

    if lower_path.endswith("readme.md") or "/docs/" in lower_path:
        score -= 8

    return score, first_line


def _qdrant_collection_exists(client) -> bool:
    try:
        collections = client.get_collections()
    except Exception:
        return False

    names = {collection.name for collection in collections.collections}
    return settings.qdrant_collection in names


def _find_line_number(text: str, keyword: str) -> int:
    index = text.find(keyword)
    if index == -1:
        return 1
    return text[:index].count("\n") + 1
