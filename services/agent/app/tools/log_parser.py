"""Lightweight log parser. Detects timestamps, levels, and key error patterns."""
import re
from dataclasses import dataclass


LOG_LINE_PATTERN = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[.,\d]*)\s+"
    r"(?P<level>TRACE|DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL)?\s*"
    r"(?P<rest>.*)$",
    re.IGNORECASE,
)


@dataclass
class ParsedLogEntry:
    timestamp: str | None
    level: str | None
    message: str
    raw: str


def parse_log_content(content: str, max_lines: int = 500) -> list[ParsedLogEntry]:
    """Parse a chunk of log content into structured entries."""
    entries = []
    for line in content.split("\n")[:max_lines]:
        if not line.strip():
            continue
        m = LOG_LINE_PATTERN.match(line)
        if m:
            entries.append(ParsedLogEntry(
                timestamp=m.group("ts"),
                level=(m.group("level") or "").upper(),
                message=m.group("rest"),
                raw=line,
            ))
        else:
            entries.append(ParsedLogEntry(
                timestamp=None, level=None, message=line, raw=line,
            ))
    return entries


def summarize_log(entries: list[ParsedLogEntry]) -> str:
    """Build a compact summary string suitable for sending to the LLM."""
    error_lines = [e for e in entries if e.level in ("ERROR", "FATAL", "CRITICAL")]
    warn_lines = [e for e in entries if e.level in ("WARN", "WARNING")]
    summary = (
        f"Total log entries: {len(entries)}\n"
        f"Errors: {len(error_lines)}\n"
        f"Warnings: {len(warn_lines)}\n\n"
        f"First error lines (up to 10):\n"
    )
    for e in error_lines[:10]:
        summary += f"  [{e.timestamp}] {e.message}\n"
    summary += "\nFirst warning lines (up to 10):\n"
    for e in warn_lines[:10]:
        summary += f"  [{e.timestamp}] {e.message}\n"
    return summary
