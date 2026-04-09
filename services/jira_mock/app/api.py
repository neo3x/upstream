"""
REST API for the Jira mock.
The Upstream agent calls these endpoints to create and manage tickets.
"""
import os
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
import httpx

from .models import Ticket, TicketCreateRequest, TicketStatus, TicketStatusUpdate
from . import storage


router = APIRouter(prefix="/api", tags=["api"])


@router.post("/tickets", response_model=Ticket, status_code=201)
def create_ticket(req: TicketCreateRequest):
    ticket = Ticket(**req.model_dump())
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
    t.status = update.status
    t.updated_at = datetime.utcnow()
    if update.resolution_note:
        t.resolution_note = update.resolution_note
    storage.save_ticket(t)

    if update.status == TicketStatus.RESOLVED:
        background.add_task(fire_resolved_webhook, t)

    return t


@router.post("/reset")
def reset_storage():
    storage.reset()
    return {"status": "reset"}


def fire_resolved_webhook(ticket: Ticket):
    """Notify the agent that a ticket has been resolved."""
    agent_url = os.getenv("AGENT_WEBHOOK_URL", "http://upstream-agent:8000/webhooks/ticket-resolved")
    try:
        httpx.post(agent_url, json=ticket.model_dump(mode="json"), timeout=10.0)
    except Exception as e:
        print(f"[jira_mock] Failed to fire webhook: {e}")
