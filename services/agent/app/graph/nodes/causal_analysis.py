"""Causal analysis node: the agent's hypothesis (the heart of Upstream).

Phase 5: returns a hardcoded hypothesis that mimics the Identity scenario.
Phase 6: replaced with real LLM call + RAG.
"""
from ..state import IncidentState, CausalHypothesis, CodeReference
from ...tools.code_search import search_eshop_code
from ...observability.logging_config import get_logger

log = get_logger(__name__)


def causal_analysis_node(state: IncidentState) -> dict:
    # Real semantic search to validate the index works
    refs = search_eshop_code("token validation in Ordering", top_k=3)
    log.info("causal.code_search", results=len(refs))

    code_refs = [
        CodeReference(
            file_path=r["file_path"],
            start_line=r["start_line"],
            end_line=r["end_line"],
            excerpt=r["text"][:300],
            relevance_score=r["score"],
        )
        for r in refs
    ]

    # MOCK hypothesis (Phase 6 will use real LLM)
    hypothesis = CausalHypothesis(
        reporter_diagnosis="The reporter believes the issue is in Ordering.",
        agent_diagnosis="Logs show 401 from Identity preceding every 500 in Ordering. Likely root cause is in Identity.API.",
        agrees_with_reporter=False,
        suspected_root_service="Identity.API",
        blast_radius=["Ordering.API", "Basket.API", "WebApp"],
        reasoning="Pattern of 401→500 cascade indicates upstream auth failure.",
        code_references=code_refs,
        confidence=0.85,
    )
    return {"hypothesis": hypothesis}
