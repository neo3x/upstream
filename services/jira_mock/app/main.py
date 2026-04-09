"""
Jira Mock — entry point.
A mocked ticket system for the Upstream SRE agent.
"""
from fastapi import FastAPI
from .logging_config import configure_logging
from .api import router as api_router
from .ui import router as ui_router


configure_logging()

app = FastAPI(
    title="Jira Mock",
    description="Mocked ticket system for the Upstream SRE agent",
    version="1.0.0",
)

app.include_router(api_router)
app.include_router(ui_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "jira_mock"}
