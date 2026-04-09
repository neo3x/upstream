"""LangGraph builder: assembles the nodes into the incident triage graph."""
from langgraph.graph import StateGraph, END, START
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

from .state import IncidentState
from .nodes.guardrails import guardrails_node
from .nodes.extraction import extraction_node
from .nodes.causal_analysis import causal_analysis_node
from .nodes.severity import severity_node
from .nodes.ticket_creation import ticket_creation_node
from .nodes.notification import notification_node
from ..config import settings


def route_after_guardrails(state: IncidentState) -> str:
    return "extraction" if state.get("guardrails_passed") else END


def build_incident_graph():
    workflow = StateGraph(IncidentState)

    workflow.add_node("guardrails", guardrails_node)
    workflow.add_node("extraction", extraction_node)
    workflow.add_node("causal_analysis", causal_analysis_node)
    workflow.add_node("assess_severity", severity_node)
    workflow.add_node("ticket_creation", ticket_creation_node)
    workflow.add_node("notification", notification_node)

    workflow.add_edge(START, "guardrails")
    workflow.add_conditional_edges("guardrails", route_after_guardrails, {
        "extraction": "extraction",
        END: END,
    })
    workflow.add_edge("extraction", "causal_analysis")
    workflow.add_edge("causal_analysis", "assess_severity")
    workflow.add_edge("assess_severity", "ticket_creation")
    workflow.add_edge("ticket_creation", "notification")
    workflow.add_edge("notification", END)

    import os
    os.makedirs(os.path.dirname(settings.checkpoint_db_path), exist_ok=True)
    conn = sqlite3.connect(settings.checkpoint_db_path, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    return workflow.compile(checkpointer=checkpointer)


def export_diagram(graph, output_path: str):
    """Export the graph as a PNG diagram for the architecture documentation."""
    try:
        png = graph.get_graph().draw_mermaid_png()
        with open(output_path, "wb") as f:
            f.write(png)
        return True
    except Exception:
        return False
