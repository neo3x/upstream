"""
Pydantic models for the Jira mock service.
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from uuid import uuid4


class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"


class TicketSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TicketEvidence(BaseModel):
    """A single piece of evidence the agent attached to support its hypothesis."""
    type: str  # "log_excerpt" | "code_reference" | "screenshot_finding"
    content: str
    source: Optional[str] = None  # file path or log line range


class Ticket(BaseModel):
    id: str = Field(default_factory=lambda: f"UPSTREAM-{uuid4().hex[:8].upper()}")
    title: str
    reporter: str
    reporter_email: str
    reported_symptom: str
    agent_hypothesis: str
    suspected_service: str
    blast_radius: list[str] = Field(default_factory=list)
    severity: TicketSeverity
    status: TicketStatus = TicketStatus.OPEN
    assigned_team: str
    evidence: list[TicketEvidence] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    resolution_note: Optional[str] = None
    incident_id: Optional[str] = None  # correlation id from agent


class TicketCreateRequest(BaseModel):
    title: str
    reporter: str
    reporter_email: str
    reported_symptom: str
    agent_hypothesis: str
    suspected_service: str
    blast_radius: list[str] = Field(default_factory=list)
    severity: TicketSeverity
    assigned_team: str
    evidence: list[TicketEvidence] = Field(default_factory=list)
    incident_id: Optional[str] = None


class TicketStatusUpdate(BaseModel):
    status: TicketStatus
    resolution_note: Optional[str] = None
