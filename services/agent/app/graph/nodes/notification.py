from ..state import IncidentState, NotificationResult
from ...tools.notification_client import send_notification
from ...observability.logging_config import get_logger

log = get_logger(__name__)


def notification_node(state: IncidentState) -> dict:
    hyp = state["hypothesis"]
    sev = state["severity"]
    ticket = state["ticket"]

    notif = send_notification({
        "type": "team_alert",
        "channel": "email",
        "recipient": f"{sev.suggested_team}@example.com",
        "subject": f"[{sev.level.upper()}] {hyp.suspected_root_service} — {ticket.ticket_id}",
        "body": f"Upstream detected a likely root cause in {hyp.suspected_root_service}.\n\n"
                f"Reporter said: {hyp.reporter_diagnosis}\n"
                f"Agent says: {hyp.agent_diagnosis}\n\n"
                f"Ticket: {ticket.ticket_url}",
        "related_ticket_id": ticket.ticket_id,
        "related_incident_id": state["incident_id"],
    })
    log.info("notification.sent", notification_id=notif["id"])
    return {"notifications": NotificationResult(notification_ids=[notif["id"]])}
