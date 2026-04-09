from ..state import IncidentState, SeverityAssessment
from ...observability.langfuse_setup import start_observation
from ...observability.logging_config import get_logger

log = get_logger(__name__)


def severity_node(state: IncidentState) -> dict:
    with start_observation(name="severity", as_type="evaluator") as span:
        hyp = state.get("hypothesis")
        blast = len(hyp.blast_radius) if hyp else 0
        suspected = (hyp.suspected_root_service if hyp else "").lower()
        reporter = (hyp.reporter_diagnosis if hyp else "").lower()
        diagnosis = (hyp.agent_diagnosis if hyp else "").lower()
        reasoning = (hyp.reasoning if hyp else "").lower()
        summary = " ".join(part for part in (reporter, diagnosis, reasoning) if part)

        if any(token in summary for token in ("auth completely down", "checkout completely down", "payment completely down")):
            level = "critical"
        elif blast >= 2 or any(
            token in summary
            for token in ("customer", "customers", "user", "users", "checkout", "payment", "pay", "pending payment", "multiple users")
        ):
            level = "high"
        else:
            level = "medium"

        if any(token in suspected for token in ("identity", "auth")):
            suggested = "identity-team"
        elif any(token in suspected for token in ("rabbitmq", "eventbus", "messaging")):
            suggested = "messaging-team"
        else:
            suggested = "ordering-team"

        result = SeverityAssessment(
            level=level,
            rationale=f"Blast radius of {blast} services indicates {level} severity.",
            suggested_team=suggested,
        )
        if span is not None:
            span.update(output=result.model_dump())
        log.info("severity.assessed", level=level, team=suggested)
        return {"severity": result}
