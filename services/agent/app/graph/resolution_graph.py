"""Smaller graph triggered when a ticket is marked resolved."""
from langgraph.graph import StateGraph, END, START
from typing import TypedDict, Optional
from ..tools.notification_client import send_notification
from ..observability.logging_config import get_logger

log = get_logger(__name__)


class ResolutionState(TypedDict, total=False):
    ticket_id: str
    reporter_email: str
    reporter_name: str
    resolution_note: Optional[str]
    suspected_service: str
    notification_id: Optional[str]


def notify_reporter_node(state: ResolutionState) -> dict:
    notif = send_notification({
        "type": "reporter_update",
        "channel": "email",
        "recipient": state["reporter_email"],
        "subject": f"Resolved: {state['ticket_id']}",
        "body": f"Hi {state.get('reporter_name', 'there')},\n\n"
                f"Your incident report has been resolved.\n"
                f"Root cause was identified in {state.get('suspected_service', 'unknown')}.\n"
                f"Resolution note: {state.get('resolution_note') or 'no additional notes'}\n",
        "related_ticket_id": state["ticket_id"],
    })
    log.info("resolution.notified", notification_id=notif["id"])
    return {"notification_id": notif["id"]}


def build_resolution_graph():
    workflow = StateGraph(ResolutionState)
    workflow.add_node("notify_reporter", notify_reporter_node)
    workflow.add_edge(START, "notify_reporter")
    workflow.add_edge("notify_reporter", END)
    return workflow.compile()
