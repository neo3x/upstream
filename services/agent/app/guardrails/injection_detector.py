"""Combines pattern matching with optional LLM-based verification."""
from .patterns import find_injection_patterns
from ..observability.logging_config import get_logger

log = get_logger(__name__)


class InjectionDetectionResult:
    def __init__(self, is_malicious: bool, reasons: list[str], severity: str):
        self.is_malicious = is_malicious
        self.reasons = reasons
        self.severity = severity


def detect_injection(
    text: str,
    log_content: str | None = None,
) -> InjectionDetectionResult:
    """Run pattern detection on text and log content."""
    reasons: list[str] = []

    text_matches = find_injection_patterns(text)
    if text_matches:
        reasons.extend([f"In text: {match}" for match in text_matches])

    if log_content:
        log_matches = find_injection_patterns(log_content)
        if log_matches:
            reasons.extend([f"In log file: {match}" for match in log_matches])

    if not reasons:
        return InjectionDetectionResult(is_malicious=False, reasons=[], severity="low")

    lowered = " ".join(reasons).lower()
    if len(reasons) >= 3 or "credential" in lowered or "system override" in lowered:
        severity = "high"
    elif reasons:
        severity = "medium"
    else:
        severity = "low"

    log.warning("guardrails.injection_detected", count=len(reasons), severity=severity)
    return InjectionDetectionResult(is_malicious=True, reasons=reasons, severity=severity)

