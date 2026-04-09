"""Incident submission endpoint."""
from fastapi import APIRouter, UploadFile, Form, File
from typing import Optional
import base64

from ..config import settings
from ..graph.builder import build_incident_graph
from ..graph.state import IncidentState
from ..observability.correlation import new_incident_id, bind_incident
from ..observability.logging_config import get_logger

router = APIRouter(prefix="/incidents", tags=["incidents"])
log = get_logger(__name__)

_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_incident_graph()
    return _graph


@router.post("")
async def submit_incident(
    text: str = Form(...),
    reporter_name: str = Form("anonymous"),
    reporter_email: str = Form("anonymous@example.com"),
    llm_provider: Optional[str] = Form(None),
    log_file: UploadFile = File(...),
    screenshot: Optional[UploadFile] = File(None),
):
    incident_id = new_incident_id()
    bind_incident(incident_id)

    log_file_bytes = await log_file.read()
    log_content = log_file_bytes.decode("utf-8", errors="replace")
    log_bytes_b64 = base64.b64encode(log_file_bytes).decode("ascii")
    image_b64 = None
    image_filename = None
    image_content_type = None
    if screenshot:
        image_bytes = await screenshot.read()
        image_b64 = base64.b64encode(image_bytes).decode("ascii")
        image_filename = screenshot.filename
        image_content_type = screenshot.content_type

    initial_state: IncidentState = {
        "incident_id": incident_id,
        "raw_text": text,
        "log_content": log_content,
        "log_bytes_b64": log_bytes_b64,
        "log_filename": log_file.filename,
        "log_content_type": log_file.content_type,
        "image_b64": image_b64,
        "image_filename": image_filename,
        "image_content_type": image_content_type,
        "reporter_name": reporter_name,
        "reporter_email": reporter_email,
        "llm_provider": llm_provider or settings.llm_provider,
        "errors": [],
    }

    log.info("incident.submitted", reporter=reporter_email)
    graph = get_graph()
    config = {"configurable": {"thread_id": incident_id}}
    final_state = graph.invoke(initial_state, config=config)

    if not final_state.get("guardrails_passed"):
        return {
            "incident_id": incident_id,
            "status": "rejected",
            "reason": final_state.get("guardrails_reason"),
        }

    return {
        "incident_id": incident_id,
        "status": "processed",
        "ticket_id": final_state["ticket"].ticket_id,
        "ticket_url": final_state["ticket"].ticket_url,
        "agent_diagnosis": final_state["hypothesis"].agent_diagnosis,
        "reasoning": final_state["hypothesis"].reasoning,
        "suspected_service": final_state["hypothesis"].suspected_root_service,
        "agrees_with_reporter": final_state["hypothesis"].agrees_with_reporter,
        "confidence": final_state["hypothesis"].confidence,
        "severity": final_state["severity"].level,
        "assigned_team": final_state["severity"].suggested_team,
    }
