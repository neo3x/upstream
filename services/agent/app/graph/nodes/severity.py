from ..state import IncidentState, SeverityAssessment
from ...observability.logging_config import get_logger

log = get_logger(__name__)


def severity_node(state: IncidentState) -> dict:
    hyp = state.get("hypothesis")
    blast = len(hyp.blast_radius) if hyp else 0
    level = "high" if blast >= 2 else "medium"
    suggested = "identity-team" if hyp and "Identity" in hyp.suspected_root_service else "ordering-team"
    log.info("severity.assessed", level=level, team=suggested)
    return {"severity": SeverityAssessment(
        level=level,
        rationale=f"Blast radius of {blast} services indicates {level} severity.",
        suggested_team=suggested,
    )}
