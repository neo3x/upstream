"""LangGraph state definition for the incident triage flow."""
from typing import Optional, TypedDict
from pydantic import BaseModel


class ExtractedSymptoms(BaseModel):
    """What the extraction node produces from the multimodal input."""
    described_problem: str
    mentioned_services: list[str] = []
    error_codes: list[str] = []
    timestamp_range: Optional[str] = None
    severity_clues: list[str] = []
    log_summary: str = ""
    image_findings: Optional[str] = None


class CodeReference(BaseModel):
    """A reference to a specific piece of code in the eShop snapshot."""
    file_path: str
    start_line: int
    end_line: int
    excerpt: str
    relevance_score: float


class CausalHypothesis(BaseModel):
    """The agent's analysis of what's actually happening."""
    reporter_diagnosis: str
    agent_diagnosis: str
    agrees_with_reporter: bool
    suspected_root_service: str
    blast_radius: list[str] = []
    reasoning: str
    code_references: list[CodeReference] = []
    confidence: float


class SeverityAssessment(BaseModel):
    level: str  # "low" | "medium" | "high" | "critical"
    rationale: str
    suggested_team: str


class TicketCreationResult(BaseModel):
    ticket_id: str
    ticket_url: str


class NotificationResult(BaseModel):
    notification_ids: list[str] = []


class IncidentState(TypedDict, total=False):
    # Identification
    incident_id: str

    # Raw input
    raw_text: str
    log_content: str
    image_b64: Optional[str]
    reporter_name: str
    reporter_email: str

    # Provider selection (per-request)
    llm_provider: str

    # Outputs of each node
    guardrails_passed: bool
    guardrails_reason: Optional[str]
    extracted: Optional[ExtractedSymptoms]
    hypothesis: Optional[CausalHypothesis]
    severity: Optional[SeverityAssessment]
    ticket: Optional[TicketCreationResult]
    notifications: Optional[NotificationResult]

    # Error tracking
    errors: list[str]
