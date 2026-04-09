"""
HTML UI for the Notification mock.
Renders an inbox-style view grouped by notification type.
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from .models import NotificationType
from . import storage


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def inbox(request: Request):
    notifications = storage.list_notifications()
    # Newest first
    notifications = sorted(notifications, key=lambda n: n.sent_at, reverse=True)
    grouped = {
        "team_alert": [n for n in notifications if n.type == NotificationType.TEAM_ALERT],
        "reporter_update": [n for n in notifications if n.type == NotificationType.REPORTER_UPDATE],
        "security_alert": [n for n in notifications if n.type == NotificationType.SECURITY_ALERT],
    }
    return templates.TemplateResponse(
        "inbox.html",
        {"request": request, "notifications": notifications, "grouped": grouped, "total": len(notifications)},
    )
