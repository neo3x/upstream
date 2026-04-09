"""Webhook endpoint for ticket resolution callbacks from the Jira mock."""
from contextlib import nullcontext
from fastapi import APIRouter, Request
from ..graph.resolution_graph import build_resolution_graph
from ..observability.correlation import bind_incident
from ..observability.langfuse_setup import (
    flush_langfuse,
    propagate_trace_attributes,
    start_observation,
    trace_id_for_incident,
)
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
    incident_id = request.headers.get("X-Incident-Id") or ticket.get("incident_id")
    bind_incident(incident_id)
    log.info("webhook.ticket_resolved", ticket_id=ticket.get("id"))
    state = {
        "incident_id": incident_id,
        "ticket_id": ticket["id"],
        "reporter_email": ticket["reporter_email"],
        "reporter_name": ticket["reporter"],
        "suspected_service": ticket.get("suspected_service", "unknown"),
        "resolution_note": ticket.get("resolution_note"),
    }
    graph = get_resolution_graph()
    trace_id = trace_id_for_incident(incident_id)

    with start_observation(
        name="ticket_resolved_webhook",
        as_type="event",
        trace_id=trace_id,
        input={"ticket_id": ticket.get("id"), "resolution_note": ticket.get("resolution_note")},
        metadata={"suspected_service": ticket.get("suspected_service", "unknown")},
        user_id=ticket.get("reporter_email"),
        session_id=incident_id,
    ) as root_observation:
        trace_attrs = propagate_trace_attributes(
            user_id=ticket.get("reporter_email"),
            session_id=incident_id,
            trace_name="incident_triage",
            metadata={"webhook": "ticket_resolved"},
        ) if root_observation is not None else nullcontext()
        with trace_attrs:
            final = graph.invoke(state)
        result = {"status": "notified", "notification_id": final.get("notification_id")}
        if root_observation is not None:
            root_observation.update(output=result)

    flush_langfuse()
    return result
