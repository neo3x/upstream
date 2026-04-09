"""Extraction node: multimodal symptom extraction.

Phase 5: returns hardcoded mock symptoms.
Phase 6: replaced with real LLM call.
"""
from ..state import IncidentState, ExtractedSymptoms
from ...tools.log_parser import parse_log_content, summarize_log
from ...observability.logging_config import get_logger

log = get_logger(__name__)


def extraction_node(state: IncidentState) -> dict:
    entries = parse_log_content(state.get("log_content", ""))
    summary = summarize_log(entries)
    log.info("extraction.parsed", log_entries=len(entries))

    # MOCK extraction (Phase 6 will use real LLM)
    extracted = ExtractedSymptoms(
        described_problem=state.get("raw_text", "")[:200],
        mentioned_services=["Ordering"],
        error_codes=["500"],
        timestamp_range="2025-04-08T10:00 - 10:30",
        severity_clues=["users affected", "production"],
        log_summary=summary,
        image_findings=None,
    )
    return {"extracted": extracted}
