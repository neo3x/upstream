"""Correlation ID management for tracing incidents end-to-end."""
import uuid
import structlog


def new_incident_id() -> str:
    return f"INC-{uuid.uuid4().hex[:10].upper()}"


def bind_incident(incident_id: str):
    """Bind the incident_id to the current logging context."""
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(incident_id=incident_id)
