"""HTTP client for the Notification mock service."""
import httpx
from ..config import settings


def send_notification(payload: dict) -> dict:
    with httpx.Client(timeout=10.0) as client:
        r = client.post(f"{settings.notification_mock_url}/api/notifications", json=payload)
        r.raise_for_status()
        return r.json()
