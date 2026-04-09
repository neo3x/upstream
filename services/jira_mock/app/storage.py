"""
File-based storage for the Jira mock.
Tickets are persisted in /app/data/tickets.json so they survive container restarts
unless the volume is wiped.
"""
import json
import os
from pathlib import Path
from typing import Optional
from threading import Lock

from .models import Ticket


STORAGE_PATH = Path(os.getenv("STORAGE_PATH", "/app/data/tickets.json"))
_lock = Lock()


def _ensure_storage():
    STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not STORAGE_PATH.exists():
        STORAGE_PATH.write_text("[]")


def list_tickets() -> list[Ticket]:
    _ensure_storage()
    with _lock:
        raw = json.loads(STORAGE_PATH.read_text())
        return [Ticket(**t) for t in raw]


def get_ticket(ticket_id: str) -> Optional[Ticket]:
    for t in list_tickets():
        if t.id == ticket_id:
            return t
    return None


def save_ticket(ticket: Ticket) -> Ticket:
    _ensure_storage()
    with _lock:
        raw = json.loads(STORAGE_PATH.read_text())
        found = False
        for i, t in enumerate(raw):
            if t["id"] == ticket.id:
                raw[i] = json.loads(ticket.model_dump_json())
                found = True
                break
        if not found:
            raw.append(json.loads(ticket.model_dump_json()))
        STORAGE_PATH.write_text(json.dumps(raw, indent=2, default=str))
    return ticket


def reset() -> None:
    _ensure_storage()
    with _lock:
        STORAGE_PATH.write_text("[]")
