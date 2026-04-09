"""Incident submission endpoint."""
from contextlib import nullcontext
from fastapi import APIRouter, UploadFile, Form, File, Request
from typing import Optional
import base64

from ..config import settings
from ..graph.builder import build_incident_graph
from ..graph.state import IncidentState
from ..observability.correlation import new_incident_id, bind_incident
from ..observability.langfuse_setup import (
    flush_langfuse,
    get_trace_url,
    propagate_trace_attributes,
    start_observation,
    trace_id_for_incident,
)
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
    request: Request,
    text: str = Form(...),
    reporter_name: str = Form("anonymous"),
    reporter_email: str = Form("anonymous@example.com"),
    llm_provider: Optional[str] = Form(None),
    log_file: UploadFile = File(...),
    screenshot: Optional[UploadFile] = File(None),
):
    incident_id = request.headers.get("X-Incident-Id") or new_incident_id()
    bind_incident(incident_id)
    selected_provider = llm_provider or settings.llm_provider

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
        "llm_provider": selected_provider,
        "errors": [],
    }

    trace_id = trace_id_for_incident(incident_id)
    trace_metadata = {
        "provider": selected_provider,
        "has_screenshot": str(bool(image_b64)),
    }

    log.info(
        "incident.submitted",
        reporter=reporter_email,
        provider=selected_provider,
        log_size_bytes=len(log_file_bytes),
    )

    graph = get_graph()
    config = {"configurable": {"thread_id": incident_id}}
    final_state = None
    result = None

    with start_observation(
        name="incident_triage",
        as_type="agent",
        trace_id=trace_id,
        input={"text": text[:500], "log_size_bytes": len(log_file_bytes)},
        metadata=trace_metadata,
        user_id=reporter_email,
        session_id=incident_id,
    ) as root_observation:
        trace_attrs = propagate_trace_attributes(
            user_id=reporter_email,
            session_id=incident_id,
            trace_name="incident_triage",
            metadata=trace_metadata,
        ) if root_observation is not None else nullcontext()

        try:
            with trace_attrs:
                final_state = graph.invoke(initial_state, config=config)
                if not final_state.get("guardrails_passed"):
                    result = {
                        "incident_id": incident_id,
                        "status": "rejected",
                        "reason": final_state.get("guardrails_reason"),
                    }
                else:
                    result = {
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
                if root_observation is not None:
                    root_observation.update(output=result)
        except Exception as exc:
            if root_observation is not None:
                root_observation.update(level="ERROR", status_message=str(exc))
            flush_langfuse()
            raise

    trace_url = get_trace_url(trace_id)
    if trace_url:
        log.info("incident.trace_ready", trace_url=trace_url)
    flush_langfuse()
    return result
