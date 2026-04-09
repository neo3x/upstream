"""HTTP client for the Notification mock service."""
import httpx
from ..config import settings


def send_notification(payload: dict) -> dict:
    incident_id = payload.get("related_incident_id") or payload.get("incident_id")
    headers = {"X-Incident-Id": incident_id} if incident_id else None
    with httpx.Client(timeout=10.0) as client:
        r = client.post(f"{settings.notification_mock_url}/api/notifications", json=payload, headers=headers)
        r.raise_for_status()
        return r.json()
