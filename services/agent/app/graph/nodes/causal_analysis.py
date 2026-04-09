"""Causal analysis node: agent hypothesis grounded in extracted symptoms and RAG."""
from ..state import IncidentState, CausalHypothesis, CodeReference
from ...llm.factory import get_llm_provider
from ...observability.langfuse_setup import start_observation
from ...observability.logging_config import get_logger
from ...prompts.causal_analysis import CAUSAL_ANALYSIS_PROMPT
from ...prompts.system import SYSTEM_PROMPT

log = get_logger(__name__)


def _select_attached_refs(refs: list[dict], limit: int = 3, preferred_service: str | None = None) -> list[dict]:
    preferred = (preferred_service or "").lower()
    ordered_refs = refs
    if preferred:
        ordered_refs = sorted(
            refs,
            key=lambda ref: (
                0
                if preferred in str(ref.get("service", "")).lower()
                or preferred in str(ref.get("file_path", "")).lower()
                else 1,
                -float(ref.get("score", 0.0)),
            ),
        )

    chosen: list[dict] = []
    seen_services: set[str] = set()

    for ref in ordered_refs:
        service = str(ref.get("service") or "")
        if service and service not in seen_services:
            chosen.append(ref)
            seen_services.add(service)
        if len(chosen) == limit:
            return chosen

    for ref in ordered_refs:
        if ref in chosen:
            continue
        chosen.append(ref)
        if len(chosen) == limit:
            break

    return chosen


def _reporter_explicitly_blames_service(text: str) -> bool:
    lower = text.lower()
    blame_markers = (
        "i think the problem is",
        "i think it's",
        "i think it is",
        "the problem is there",
        "the issue is in",
        "the problem is in",
        "i believe the problem is",
    )
    return any(marker in lower for marker in blame_markers)


def _reporter_is_uncertain(text: str) -> bool:
    lower = text.lower()
    uncertainty_markers = (
        "what's going on",
        "what is going on",
        "not sure",
        "unsure",
        "don't know",
        "do not know",
        "no idea",
        "don't see any errors",
        "do not see any errors",
    )
    return any(marker in lower for marker in uncertainty_markers)


def _normalize_hypothesis(hypothesis: CausalHypothesis, state: IncidentState) -> CausalHypothesis:
    raw_text = state.get("raw_text", "")
    if _reporter_is_uncertain(raw_text) and not _reporter_explicitly_blames_service(raw_text):
        hypothesis.agrees_with_reporter = True
    return hypothesis


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
            for ref in _select_attached_refs(
                refs,
                preferred_service=(
                    extracted.mentioned_services[-1]
                    if extracted and extracted.mentioned_services
                    else None
                ),
            )
        ],
        confidence=0.0,
    )


def causal_analysis_node(state: IncidentState) -> dict:
    with start_observation(
        name="causal_analysis",
        as_type="span",
        input={"provider": state.get("llm_provider")},
        metadata={"incident_id": state.get("incident_id")},
    ) as span:
        extracted = state.get("extracted")
        if extracted is None:
            reason = "causal_analysis: no extracted symptoms"
            log.error("causal.missing_extraction")
            fallback = _fallback_hypothesis(state, None, [], reason)
            if span is not None:
                span.update(level="ERROR", status_message=reason, output={"fallback": True})
            return {
                "hypothesis": fallback,
                "errors": [*state.get("errors", []), reason],
            }

        query_parts = [extracted.described_problem]
        if extracted.mentioned_services:
            query_parts.append("services: " + ", ".join(extracted.mentioned_services))
        if extracted.error_codes:
            query_parts.append("errors: " + ", ".join(extracted.error_codes))
        if extracted.severity_clues:
            query_parts.append("clues: " + ", ".join(extracted.severity_clues))
        if extracted.log_summary:
            query_parts.append("log_summary: " + extracted.log_summary)
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
                temperature=0.0,
            )
            hypothesis = _normalize_hypothesis(hypothesis, state)
            attached_refs = _select_attached_refs(refs, preferred_service=hypothesis.suspected_root_service)
            hypothesis.code_references = [
                CodeReference(
                    file_path=ref["file_path"],
                    start_line=ref["start_line"],
                    end_line=ref["end_line"],
                    excerpt=ref["text"][:300],
                    relevance_score=ref["score"],
                )
                for ref in attached_refs
            ]
            if span is not None:
                span.update(
                    output={
                        "agrees_with_reporter": hypothesis.agrees_with_reporter,
                        "suspected_root_service": hypothesis.suspected_root_service,
                    }
                )
            log.info("causal.hypothesis", agrees=hypothesis.agrees_with_reporter)
            result = {"hypothesis": hypothesis}
            if base_errors:
                result["errors"] = base_errors
            return result
        except Exception as exc:
            log.error("causal.failed", error=str(exc))
            reason = f"causal_analysis: {exc}"
            fallback_hypothesis = _normalize_hypothesis(
                _fallback_hypothesis(state, extracted, refs, str(exc)),
                state,
            )
            if span is not None:
                span.update(
                    level="ERROR",
                    status_message=str(exc),
                    output={"fallback_service": fallback_hypothesis.suspected_root_service},
                )
            return {
                "hypothesis": fallback_hypothesis,
                "errors": [*base_errors, reason],
            }
