"""Curated patterns of prompt injection and malicious instructions.

This list is intentionally conservative and additive. False positives are
acceptable; false negatives are not.
"""
import re


INJECTION_PATTERNS = [
    re.compile(
        r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules)",
        re.IGNORECASE,
    ),
    re.compile(r"disregard\s+(all\s+)?(previous|prior|above)", re.IGNORECASE),
    re.compile(
        r"forget\s+(your|all|previous)\s+(instructions|rules|prompts)",
        re.IGNORECASE,
    ),
    re.compile(r"you\s+are\s+now\s+", re.IGNORECASE),
    re.compile(r"act\s+as\s+(a|an)\s+", re.IGNORECASE),
    re.compile(r"pretend\s+(to\s+be|you\s+are)", re.IGNORECASE),
    re.compile(r"roleplay\s+as", re.IGNORECASE),
    re.compile(
        r"(reveal|show|print|output)\s+(your|the)\s+(system\s+)?prompt",
        re.IGNORECASE,
    ),
    re.compile(r"what\s+(are|were)\s+your\s+instructions", re.IGNORECASE),
    re.compile(r"^\s*system\s*:", re.IGNORECASE | re.MULTILINE),
    re.compile(r"\[\s*system\s*\]", re.IGNORECASE),
    re.compile(r"<\s*system\s*>", re.IGNORECASE),
    re.compile(r"###\s*system", re.IGNORECASE),
    re.compile(
        r"(admin|administrator|root|sudo)\s*:\s*new\s+(directive|instruction|order)",
        re.IGNORECASE,
    ),
    re.compile(r"new\s+directive\s+from", re.IGNORECASE),
    re.compile(r"(send|email|post)\s+(this|the\s+following)\s+to", re.IGNORECASE),
    re.compile(
        r"(execute|run|invoke)\s+(the\s+)?(following|this)\s+(command|tool|function)",
        re.IGNORECASE,
    ),
    re.compile(r"(api[_\s-]?key|password|secret|credential|token)\s*[:=]", re.IGNORECASE),
    re.compile(r"<\s*script", re.IGNORECASE),
    re.compile(r"<\s*iframe", re.IGNORECASE),
]

SUSPICIOUS_LOG_PATTERNS = [
    re.compile(r"\bSYSTEM\s+OVERRIDE\b", re.IGNORECASE),
    re.compile(r"\bAGENT\s+DIRECTIVE\b", re.IGNORECASE),
    re.compile(r"\bIMMEDIATE\s+ACTION\s+REQUIRED\b", re.IGNORECASE),
]


def find_injection_patterns(text: str) -> list[str]:
    """Return a list of pattern descriptions that matched."""
    matches: list[str] = []
    for pattern in INJECTION_PATTERNS:
        found = pattern.search(text)
        if found:
            matches.append(f"injection: {found.group(0)[:80]}")
    for pattern in SUSPICIOUS_LOG_PATTERNS:
        found = pattern.search(text)
        if found:
            matches.append(f"suspicious_log: {found.group(0)[:80]}")
    return matches

