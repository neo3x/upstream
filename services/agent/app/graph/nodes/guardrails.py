"""Guardrails node: input validation and prompt injection detection.

In this phase: simple keyword check (full implementation in Phase 7).
"""
from ..state import IncidentState
from ...observability.logging_config import get_logger

log = get_logger(__name__)

INJECTION_KEYWORDS = [
    "ignore previous", "ignore all instructions", "system:", "you are now",
    "disregard", "forget your instructions",
]


def guardrails_node(state: IncidentState) -> dict:
    text = (state.get("raw_text", "") + " " + state.get("log_content", "")).lower()
    for kw in INJECTION_KEYWORDS:
        if kw in text:
            log.warning("guardrails.injection_detected", keyword=kw)
            return {"guardrails_passed": False, "guardrails_reason": f"Detected suspicious phrase: '{kw}'"}
    log.info("guardrails.passed")
    return {"guardrails_passed": True}
