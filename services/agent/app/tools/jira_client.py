"""HTTP client for the Jira mock service."""
import httpx
from ..config import settings


def create_ticket(payload: dict) -> dict:
    with httpx.Client(timeout=10.0) as client:
        r = client.post(f"{settings.jira_mock_url}/api/tickets", json=payload)
        r.raise_for_status()
        return r.json()


def get_ticket(ticket_id: str) -> dict:
    with httpx.Client(timeout=10.0) as client:
        r = client.get(f"{settings.jira_mock_url}/api/tickets/{ticket_id}")
        r.raise_for_status()
        return r.json()
