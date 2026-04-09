"""
File-based storage for the Notification mock.
Notifications are persisted in /app/data/notifications.json so they survive
container restarts unless the volume is wiped.
"""
import json
import os
from pathlib import Path
from typing import Optional
from threading import Lock

from .models import Notification


STORAGE_PATH = Path(os.getenv("STORAGE_PATH", "/app/data/notifications.json"))
_lock = Lock()


def _ensure_storage():
    STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not STORAGE_PATH.exists():
        STORAGE_PATH.write_text("[]")


def list_notifications() -> list[Notification]:
    _ensure_storage()
    with _lock:
        raw = json.loads(STORAGE_PATH.read_text())
        return [Notification(**n) for n in raw]


def get_notification(notification_id: str) -> Optional[Notification]:
    for n in list_notifications():
        if n.id == notification_id:
            return n
    return None


def save_notification(notification: Notification) -> Notification:
    _ensure_storage()
    with _lock:
        raw = json.loads(STORAGE_PATH.read_text())
        found = False
        for i, n in enumerate(raw):
            if n["id"] == notification.id:
                raw[i] = json.loads(notification.model_dump_json())
                found = True
                break
        if not found:
            raw.append(json.loads(notification.model_dump_json()))
        STORAGE_PATH.write_text(json.dumps(raw, indent=2, default=str))
    return notification


def reset() -> None:
    _ensure_storage()
    with _lock:
        STORAGE_PATH.write_text("[]")
