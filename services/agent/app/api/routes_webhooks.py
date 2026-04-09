"""Webhook endpoint for ticket resolution callbacks from the Jira mock."""
from fastapi import APIRouter, Request
from ..graph.resolution_graph import build_resolution_graph
from ..observability.logging_config import get_logger

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
log = get_logger(__name__)
_resolution_graph = None


def get_resolution_graph():
    global _resolution_graph
    if _resolution_graph is None:
        _resolution_graph = build_resolution_graph()
    return _resolution_graph


@router.post("/ticket-resolved")
async def ticket_resolved(request: Request):
    ticket = await request.json()
    log.info("webhook.ticket_resolved", ticket_id=ticket.get("id"))
    state = {
        "ticket_id": ticket["id"],
        "reporter_email": ticket["reporter_email"],
        "reporter_name": ticket["reporter"],
        "suspected_service": ticket.get("suspected_service", "unknown"),
        "resolution_note": ticket.get("resolution_note"),
    }
    graph = get_resolution_graph()
    final = graph.invoke(state)
    return {"status": "notified", "notification_id": final.get("notification_id")}
