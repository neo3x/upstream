"""Correlation ID helpers for the Notification mock service."""
from __future__ import annotations

import structlog


def bind_incident(incident_id: str | None):
    structlog.contextvars.clear_contextvars()
    if incident_id:
        structlog.contextvars.bind_contextvars(incident_id=incident_id)
