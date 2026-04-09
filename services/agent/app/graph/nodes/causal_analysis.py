"""Causal analysis node: agent hypothesis grounded in extracted symptoms and RAG."""
from ..state import IncidentState, CausalHypothesis, CodeReference
from ...llm.factory import get_llm_provider
from ...observability.logging_config import get_logger
from ...prompts.causal_analysis import CAUSAL_ANALYSIS_PROMPT
from ...prompts.system import SYSTEM_PROMPT

log = get_logger(__name__)


def _fallback_hypothesis(
    state: IncidentState,
    extracted,
    refs: list[dict],
    reason: str,
) -> CausalHypothesis:
    return CausalHypothesis(
        reporter_diagnosis=state.get("raw_text", "")[:200] or "Reporter diagnosis unavailable.",
        agent_diagnosis="Uncertain: the agent could not produce a grounded causal hypothesis.",
        agrees_with_reporter=False,
        suspected_root_service=(
            extracted.mentioned_services[0] if extracted and extracted.mentioned_services else "uncertain"
        ),
        blast_radius=extracted.mentioned_services if extracted else [],
        reasoning=f"Uncertain. Automated causal analysis failed: {reason}",
        code_references=[
            CodeReference(
                file_path=ref["file_path"],
                start_line=ref["start_line"],
                end_line=ref["end_line"],
                excerpt=ref["text"][:300],
                relevance_score=ref["score"],
            )
            for ref in refs[:3]
        ],
        confidence=0.0,
    )


def causal_analysis_node(state: IncidentState) -> dict:
    extracted = state.get("extracted")
    if extracted is None:
        reason = "causal_analysis: no extracted symptoms"
        log.error("causal.missing_extraction")
        return {
            "hypothesis": _fallback_hypothesis(state, None, [], reason),
            "errors": [*state.get("errors", []), reason],
        }

    query_parts = [extracted.described_problem]
    if extracted.mentioned_services:
        query_parts.append("services: " + ", ".join(extracted.mentioned_services))
    if extracted.error_codes:
        query_parts.append("errors: " + ", ".join(extracted.error_codes))
    query = " | ".join(part for part in query_parts if part)

    refs: list[dict] = []
    code_search_error = None
    try:
        from ...tools.code_search import search_eshop_code

        refs = search_eshop_code(query, top_k=8)
        log.info("causal.code_search", results=len(refs))
    except Exception as exc:
        code_search_error = str(exc)
        log.error("causal.code_search_failed", error=code_search_error)

    code_context = "\n\n".join(
        (
            f"--- {ref['file_path']}:{ref['start_line']}-{ref['end_line']} "
            f"(service: {ref.get('service')}, score: {ref['score']:.2f}) ---\n"
            f"{ref['text'][:600]}"
        )
        for ref in refs
    ) or "No code context available."

    user_msg = (
        f"===REPORT START===\n{state.get('raw_text', '')}\n===REPORT END===\n\n"
        "===EXTRACTED SYMPTOMS START===\n"
        f"{extracted.model_dump_json(indent=2)}\n"
        "===EXTRACTED SYMPTOMS END===\n\n"
        "===CODE CONTEXT START===\n"
        f"{code_context}\n"
        "===CODE CONTEXT END===\n\n"
        "Now form your causal hypothesis. Remember: the reporter often blames the symptom, not the cause."
    )

    base_errors = [*state.get("errors", [])]
    if code_search_error:
        base_errors.append(f"causal_analysis.code_search: {code_search_error}")

    try:
        provider = get_llm_provider(state.get("llm_provider"))
        hypothesis = provider.complete_structured(
            system=SYSTEM_PROMPT + "\n\n" + CAUSAL_ANALYSIS_PROMPT,
            user=user_msg,
            schema=CausalHypothesis,
        )
        hypothesis.code_references = [
            CodeReference(
                file_path=ref["file_path"],
                start_line=ref["start_line"],
                end_line=ref["end_line"],
                excerpt=ref["text"][:300],
                relevance_score=ref["score"],
            )
            for ref in refs[:3]
        ]
        log.info("causal.hypothesis", agrees=hypothesis.agrees_with_reporter)
        result = {"hypothesis": hypothesis}
        if base_errors:
            result["errors"] = base_errors
        return result
    except Exception as exc:
        log.error("causal.failed", error=str(exc))
        reason = f"causal_analysis: {exc}"
        return {
            "hypothesis": _fallback_hypothesis(state, extracted, refs, str(exc)),
            "errors": [*base_errors, reason],
        }
