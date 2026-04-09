"""
HTML UI for the Jira mock.
Renders a Kanban-style board so the demo video shows tickets visually.
"""
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime

from .models import TicketStatus
from . import storage


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def board(request: Request):
    tickets = storage.list_tickets()
    grouped = {
        TicketStatus.OPEN: [t for t in tickets if t.status == TicketStatus.OPEN],
        TicketStatus.IN_PROGRESS: [t for t in tickets if t.status == TicketStatus.IN_PROGRESS],
        TicketStatus.RESOLVED: [t for t in tickets if t.status == TicketStatus.RESOLVED],
    }
    return templates.TemplateResponse("board.html", {"request": request, "grouped": grouped})


@router.get("/tickets/{ticket_id}", response_class=HTMLResponse)
def ticket_detail(request: Request, ticket_id: str):
    t = storage.get_ticket(ticket_id)
    if t is None:
        raise HTTPException(404, "Ticket not found")
    return templates.TemplateResponse("ticket_detail.html", {"request": request, "ticket": t})


@router.post("/tickets/{ticket_id}/move")
def move_ticket(ticket_id: str, new_status: str = Form(...)):
    t = storage.get_ticket(ticket_id)
    if t is None:
        raise HTTPException(404, "Ticket not found")
    t.status = TicketStatus(new_status)
    t.updated_at = datetime.utcnow()
    storage.save_ticket(t)

    if t.status == TicketStatus.RESOLVED:
        from .api import fire_resolved_webhook
        fire_resolved_webhook(t)

    return RedirectResponse(f"/tickets/{ticket_id}", status_code=303)
