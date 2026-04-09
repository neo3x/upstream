"""FastAPI application entry point."""
from fastapi import FastAPI
from .observability.logging_config import configure_logging
from .api.routes_incidents import router as incidents_router
from .api.routes_webhooks import router as webhooks_router
from .api.routes_health import router as health_router


configure_logging()

app = FastAPI(
    title="Upstream Agent",
    description="Multimodal SRE intake and triage agent",
    version="0.1.0",
)

app.include_router(health_router)
app.include_router(incidents_router)
app.include_router(webhooks_router)


@app.on_event("startup")
async def on_startup():
    # Pre-build graph and export the diagram
    from .graph.builder import build_incident_graph, export_diagram
    graph = build_incident_graph()
    export_diagram(graph, "/app/data/checkpoints/architecture.png")
