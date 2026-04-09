"""Extraction node: multimodal symptom extraction via the configured LLM."""
from ..state import IncidentState, ExtractedSymptoms
from ...llm.factory import get_llm_provider
from ...observability.logging_config import get_logger
from ...prompts.extraction import EXTRACTION_PROMPT
from ...prompts.system import SYSTEM_PROMPT
from ...tools.log_parser import parse_log_content, summarize_log

log = get_logger(__name__)


def extraction_node(state: IncidentState) -> dict:
    entries = parse_log_content(state.get("log_content", ""))
    log_summary = summarize_log(entries)
    log.info("extraction.parsed", log_entries=len(entries))

    user_msg = (
        f"REPORTER TEXT:\n{state.get('raw_text', '')}\n\n"
        f"LOG SUMMARY:\n{log_summary}\n\n"
        "FULL LOG (truncated to first 200 lines):\n"
        + "\n".join(entry.raw for entry in entries[:200])
    )

    try:
        provider = get_llm_provider(state.get("llm_provider"))
        extracted = provider.complete_structured(
            system=SYSTEM_PROMPT + "\n\n" + EXTRACTION_PROMPT,
            user=user_msg,
            schema=ExtractedSymptoms,
            image_b64=state.get("image_b64"),
        )
        log.info("extraction.success", services=extracted.mentioned_services)
        return {"extracted": extracted}
    except Exception as exc:
        log.error("extraction.failed", error=str(exc))
        return {
            "extracted": ExtractedSymptoms(
                described_problem=state.get("raw_text", "")[:200],
                log_summary=log_summary,
            ),
            "errors": [*state.get("errors", []), f"extraction: {exc}"],
        }
