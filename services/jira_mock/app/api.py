"""
REST API for the Jira mock.
The Upstream agent calls these endpoints to create and manage tickets.
"""
import os
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
import httpx

from .correlation import bind_incident
from .logging_config import get_logger
from .models import Ticket, TicketCreateRequest, TicketStatus, TicketStatusUpdate
from . import storage


router = APIRouter(prefix="/api", tags=["api"])
log = get_logger(__name__)


@router.post("/tickets", response_model=Ticket, status_code=201)
def create_ticket(req: TicketCreateRequest, request: Request):
    bind_incident(request.headers.get("X-Incident-Id") or req.incident_id)
    ticket = Ticket(**req.model_dump())
    log.info("jira.ticket_created", ticket_id=ticket.id, assigned_team=ticket.assigned_team)
    return storage.save_ticket(ticket)


@router.get("/tickets", response_model=list[Ticket])
def list_all_tickets():
    return storage.list_tickets()


@router.get("/tickets/{ticket_id}", response_model=Ticket)
def get_one(ticket_id: str):
    t = storage.get_ticket(ticket_id)
    if t is None:
        raise HTTPException(404, "Ticket not found")
    return t


@router.patch("/tickets/{ticket_id}/status", response_model=Ticket)
def update_status(ticket_id: str, update: TicketStatusUpdate, background: BackgroundTasks):
    t = storage.get_ticket(ticket_id)
    if t is None:
        raise HTTPException(404, "Ticket not found")
    bind_incident(t.incident_id)
    t.status = update.status
    t.updated_at = datetime.utcnow()
    if update.resolution_note:
        t.resolution_note = update.resolution_note
    storage.save_ticket(t)

    if update.status == TicketStatus.RESOLVED:
        background.add_task(fire_resolved_webhook, t)

    log.info("jira.ticket_status_updated", ticket_id=t.id, status=t.status.value)
    return t


@router.post("/reset")
def reset_storage():
    storage.reset()
    return {"status": "reset"}


def fire_resolved_webhook(ticket: Ticket):
    """Notify the agent that a ticket has been resolved."""
    agent_url = os.getenv("AGENT_WEBHOOK_URL", "http://upstream-agent:8000/webhooks/ticket-resolved")
    try:
        headers = {"X-Incident-Id": ticket.incident_id} if ticket.incident_id else None
        httpx.post(agent_url, json=ticket.model_dump(mode="json"), headers=headers, timeout=10.0)
        log.info("jira.resolution_webhook_sent", ticket_id=ticket.id)
    except Exception as e:
        log.error("jira.resolution_webhook_failed", error=str(e), ticket_id=ticket.id)
