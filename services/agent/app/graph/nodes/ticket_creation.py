from ..state import IncidentState, TicketCreationResult
from ...tools.jira_client import create_ticket
from ...config import settings
from ...observability.logging_config import get_logger

log = get_logger(__name__)


def ticket_creation_node(state: IncidentState) -> dict:
    hyp = state["hypothesis"]
    sev = state["severity"]
    payload = {
        "title": f"[Auto] {hyp.suspected_root_service} suspected root cause",
        "reporter": state.get("reporter_name", "anonymous"),
        "reporter_email": state.get("reporter_email", "anonymous@example.com"),
        "reported_symptom": hyp.reporter_diagnosis,
        "agent_hypothesis": hyp.agent_diagnosis,
        "suspected_service": hyp.suspected_root_service,
        "blast_radius": hyp.blast_radius,
        "severity": sev.level,
        "assigned_team": sev.suggested_team,
        "evidence": [
            {"type": "code_reference", "content": ref.excerpt, "source": f"{ref.file_path}:{ref.start_line}-{ref.end_line}"}
            for ref in hyp.code_references
        ],
        "incident_id": state["incident_id"],
    }
    ticket = create_ticket(payload)
    log.info("ticket.created", ticket_id=ticket["id"])
    return {"ticket": TicketCreationResult(
        ticket_id=ticket["id"],
        ticket_url=f"{settings.jira_mock_url}/tickets/{ticket['id']}",
    )}
