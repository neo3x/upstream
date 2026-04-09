"""
REST API for the Notification mock.
The Upstream agent calls these endpoints to send notifications.
"""
from fastapi import APIRouter, HTTPException, Request

from .correlation import bind_incident
from .logging_config import get_logger
from .models import Notification, NotificationCreate
from . import storage


router = APIRouter(prefix="/api", tags=["api"])
log = get_logger(__name__)


@router.post("/notifications", response_model=Notification, status_code=201)
def send_notification(req: NotificationCreate, request: Request):
    bind_incident(request.headers.get("X-Incident-Id") or req.related_incident_id)
    n = Notification(**req.model_dump())
    log.info("notification.created", notification_id=n.id, notification_type=n.type.value)
    return storage.save_notification(n)


@router.get("/notifications", response_model=list[Notification])
def list_all():
    return storage.list_notifications()


@router.get("/notifications/{notification_id}", response_model=Notification)
def get_one(notification_id: str):
    n = storage.get_notification(notification_id)
    if n is None:
        raise HTTPException(404, "Notification not found")
    return n


@router.post("/reset")
def reset():
    storage.reset()
    return {"status": "reset"}
