"""Correlation ID helpers for the UI service."""
from __future__ import annotations

import uuid

import structlog


def new_incident_id() -> str:
    return f"INC-{uuid.uuid4().hex[:10].upper()}"


def bind_incident(incident_id: str | None):
    structlog.contextvars.clear_contextvars()
    if incident_id:
        structlog.contextvars.bind_contextvars(incident_id=incident_id)
