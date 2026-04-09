"""Guardrails node: validates inputs and detects prompt injection.

On detection, routes the incident to the security flow instead of normal triage.
"""
import base64

from ..state import IncidentState, NotificationResult, TicketCreationResult
from ...config import settings
from ...guardrails.injection_detector import detect_injection
from ...guardrails.input_validator import (
    validate_image_bytes,
    validate_log_content,
    validate_log_upload,
    validate_text,
)
from ...observability.langfuse_setup import start_observation
from ...observability.logging_config import get_logger
from ...tools.jira_client import create_ticket
from ...tools.notification_client import send_notification

log = get_logger(__name__)


def guardrails_node(state: IncidentState) -> dict:
    text = state.get("raw_text", "")
    log_content = state.get("log_content", "")
    image_b64 = state.get("image_b64")

    with start_observation(
        name="guardrails",
        as_type="guardrail",
        input={
            "text_length": len(text),
            "log_length": len(log_content),
            "has_image": bool(image_b64),
        },
    ) as span:
        text_check = validate_text(text)
        if not text_check.ok:
            result = _reject(state, f"Invalid text input: {text_check.reason}", severity="low")
            if span is not None:
                span.update(level="ERROR", status_message=text_check.reason, output=result)
            return result

        try:
            log_bytes = _decode_base64_or_fallback(
                encoded=state.get("log_bytes_b64"),
                fallback_text=log_content,
            )
        except Exception:
            result = _reject(state, "Log file could not be decoded", severity="medium")
            if span is not None:
                span.update(level="ERROR", status_message="log decode failed", output=result)
            return result

        log_upload_check = validate_log_upload(log_bytes, state.get("log_content_type"))
        if not log_upload_check.ok:
            result = _reject(state, f"Invalid log file: {log_upload_check.reason}", severity="low")
            if span is not None:
                span.update(level="ERROR", status_message=log_upload_check.reason, output=result)
            return result

        log_check = validate_log_content(log_content)
        if not log_check.ok:
            result = _reject(state, f"Invalid log file: {log_check.reason}", severity="low")
            if span is not None:
                span.update(level="ERROR", status_message=log_check.reason, output=result)
            return result

        if image_b64:
            try:
                image_bytes = base64.b64decode(image_b64, validate=True)
                image_check = validate_image_bytes(image_bytes, state.get("image_content_type"))
                if not image_check.ok:
                    result = _reject(state, f"Invalid image: {image_check.reason}", severity="low")
                    if span is not None:
                        span.update(level="ERROR", status_message=image_check.reason, output=result)
                    return result
            except Exception:
                result = _reject(state, "Image could not be decoded", severity="medium")
                if span is not None:
                    span.update(level="ERROR", status_message="image decode failed", output=result)
                return result

        detection = detect_injection(text, log_content)
        if detection.is_malicious:
            result = _reject(
                state,
                "Prompt injection detected. Reasons: " + "; ".join(detection.reasons[:3]),
                severity=detection.severity,
                create_security_ticket=True,
            )
            if span is not None:
                span.update(
                    level="ERROR",
                    status_message="prompt injection detected",
                    output={"severity": detection.severity, "reasons": detection.reasons[:3]},
                )
            return result

        result = {"guardrails_passed": True}
        if span is not None:
            span.update(output=result)
        log.info("guardrails.passed")
        return result


def _decode_base64_or_fallback(encoded: str | None, fallback_text: str) -> bytes:
    if encoded:
        return base64.b64decode(encoded, validate=True)
    return fallback_text.encode("utf-8")


def _reject(
    state: IncidentState,
    reason: str,
    severity: str,
    create_security_ticket: bool = False,
) -> dict:
    log.warning("guardrails.rejected", reason=reason, severity=severity)

    incident_id = state.get("incident_id", "unknown")
    reporter_email = state.get("reporter_email", "unknown@example.com")
    errors = [*state.get("errors", []), f"guardrails: {reason}"]
    notification_ids: list[str] = []
    result: dict = {
        "guardrails_passed": False,
        "guardrails_reason": reason,
        "errors": errors,
    }

    try:
        notif = send_notification({
            "type": "security_alert",
            "channel": "email",
            "recipient": "security-team@example.com",
            "subject": f"[SECURITY] Suspicious incident submission - {incident_id}",
            "body": (
                "Upstream rejected an incident submission.\n\n"
                f"Reporter: {reporter_email}\n"
                f"Incident ID: {incident_id}\n"
                f"Severity: {severity}\n"
                f"Reason: {reason}\n\n"
                "The submission was NOT processed by the LLM. No tools were called on its behalf."
            ),
            "related_incident_id": incident_id,
        })
        notification_ids.append(notif["id"])
        log.info("guardrails.notification_sent", notification_id=notif["id"])
    except Exception as exc:
        log.error("guardrails.notification_failed", error=str(exc))

    if notification_ids:
        result["notifications"] = NotificationResult(notification_ids=notification_ids)

    if create_security_ticket:
        try:
            ticket = create_ticket({
                "title": f"[SECURITY REVIEW] Rejected submission {incident_id}",
                "reporter": "upstream-guardrails",
                "reporter_email": reporter_email,
                "reported_symptom": "Automated rejection by Upstream guardrails",
                "agent_hypothesis": (
                    "Submission contained patterns consistent with prompt injection. "
                    f"Severity: {severity}."
                ),
                "suspected_service": "n/a",
                "blast_radius": [],
                "severity": severity,
                "assigned_team": "security-team",
                "evidence": [
                    {"type": "log_excerpt", "content": reason, "source": "guardrails"},
                ],
                "incident_id": incident_id,
            })
            result["ticket"] = TicketCreationResult(
                ticket_id=ticket["id"],
                ticket_url=f"{settings.jira_mock_url}/tickets/{ticket['id']}",
            )
            log.info("guardrails.ticket_created", ticket_id=ticket["id"])
        except Exception as exc:
            log.error("guardrails.ticket_failed", error=str(exc))

    return result
