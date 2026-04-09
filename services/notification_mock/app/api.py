"""
REST API for the Notification mock.
The Upstream agent calls these endpoints to send notifications.
"""
from fastapi import APIRouter, HTTPException

from .models import Notification, NotificationCreate
from . import storage


router = APIRouter(prefix="/api", tags=["api"])


@router.post("/notifications", response_model=Notification, status_code=201)
def send_notification(req: NotificationCreate):
    n = Notification(**req.model_dump())
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
