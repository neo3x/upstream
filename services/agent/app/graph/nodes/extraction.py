"""Extraction node: multimodal symptom extraction via the configured LLM."""
import re

from ..state import IncidentState, ExtractedSymptoms
from ...llm.factory import get_llm_provider
from ...observability.langfuse_setup import start_observation
from ...observability.logging_config import get_logger
from ...prompts.extraction import EXTRACTION_PROMPT
from ...prompts.system import SYSTEM_PROMPT
from ...tools.log_parser import parse_log_content, summarize_log

log = get_logger(__name__)
SERVICE_NAME_PATTERN = re.compile(r"\b[A-Z][A-Za-z0-9]+(?:\.[A-Z][A-Za-z0-9]+)+\b")
ERROR_CODE_CONTEXT_PATTERN = re.compile(
    r"(http|status|code|returned|returning|response|unauthorized|forbidden|timeout|bad request|not found)",
    re.IGNORECASE,
)
ERROR_CODE_PATTERN = re.compile(r"(?<![\d:.])([1-5]\d{2})(?!\d)")


def _unique_ordered(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _derive_log_timestamp_range(entries) -> str | None:
    timestamps = [entry.timestamp for entry in entries if entry.timestamp]
    if not timestamps:
        return None
    return f"{timestamps[0]} - {timestamps[-1]}"


def _derive_service_names(raw_text: str, log_content: str) -> list[str]:
    combined = f"{raw_text}\n{log_content}"
    matches = SERVICE_NAME_PATTERN.findall(combined)
    extras = []
    for label in ("RabbitMQ", "EventBus", "EventBusRabbitMQ", "WebApp"):
        if label.lower() in combined.lower():
            extras.append(label)
    return _unique_ordered(matches + extras)


def _derive_error_codes(raw_text: str, log_content: str) -> list[str]:
    codes: list[str] = []
    for line in [*raw_text.splitlines(), *log_content.splitlines()]:
        if not ERROR_CODE_CONTEXT_PATTERN.search(line):
            continue
        codes.extend(ERROR_CODE_PATTERN.findall(line))
    return _unique_ordered(codes)


def _derive_severity_clues(raw_text: str, log_content: str, entries) -> list[str]:
    combined = f"{raw_text}\n{log_content}".lower()
    clues: list[str] = []
    if any(token in combined for token in ("user", "users", "customer", "customers", "checkout", "paid")):
        clues.append("customer-visible")
    if "pending payment" in combined:
        clues.append("payment pending")
    if len(entries) >= 4 or log_content.lower().count("error") >= 2 or log_content.lower().count("warn") >= 2:
        clues.append("repeated failures")
    return _unique_ordered(clues)


def _enrich_extracted(extracted: ExtractedSymptoms, state: IncidentState, entries) -> ExtractedSymptoms:
    raw_text = state.get("raw_text", "")
    log_content = state.get("log_content", "")

    extracted.mentioned_services = _unique_ordered(
        [*extracted.mentioned_services, *_derive_service_names(raw_text, log_content)]
    )
    extracted.error_codes = _unique_ordered(
        [*extracted.error_codes, *_derive_error_codes(raw_text, log_content)]
    )
    if not extracted.timestamp_range:
        extracted.timestamp_range = _derive_log_timestamp_range(entries)
    extracted.severity_clues = _unique_ordered(
        [*extracted.severity_clues, *_derive_severity_clues(raw_text, log_content, entries)]
    )
    return extracted


def extraction_node(state: IncidentState) -> dict:
    entries = parse_log_content(state.get("log_content", ""))
    log_summary = summarize_log(entries)
    log.info("extraction.parsed", log_entries=len(entries))

    user_msg = (
        f"===REPORT START===\n{state.get('raw_text', '')}\n===REPORT END===\n\n"
        f"===LOG SUMMARY START===\n{log_summary}\n===LOG SUMMARY END===\n\n"
        "===LOG START===\n"
        + "\n".join(entry.raw for entry in entries[:200])
        + "\n===LOG END==="
    )

    with start_observation(
        name="extraction",
        as_type="span",
        input={"log_entries": len(entries), "provider": state.get("llm_provider")},
    ) as span:
        try:
            provider = get_llm_provider(state.get("llm_provider"))
            extracted = provider.complete_structured(
                system=SYSTEM_PROMPT + "\n\n" + EXTRACTION_PROMPT,
                user=user_msg,
                schema=ExtractedSymptoms,
                image_b64=state.get("image_b64"),
                temperature=0.0,
            )
            extracted = _enrich_extracted(extracted, state, entries)
            if span is not None:
                span.update(
                    output={
                        "mentioned_services": extracted.mentioned_services,
                        "error_codes": extracted.error_codes,
                    }
                )
            log.info("extraction.success", services=extracted.mentioned_services)
            return {"extracted": extracted}
        except Exception as exc:
            log.error("extraction.failed", error=str(exc))
            fallback = ExtractedSymptoms(
                described_problem=state.get("raw_text", "")[:200],
                log_summary=log_summary,
            )
            fallback = _enrich_extracted(fallback, state, entries)
            if span is not None:
                span.update(
                    level="ERROR",
                    status_message=str(exc),
                    output={"fallback_services": fallback.mentioned_services},
                )
            return {
                "extracted": fallback,
                "errors": [*state.get("errors", []), f"extraction: {exc}"],
            }
