"""
Notification Mock — entry point.
A mocked notification system for the Upstream SRE agent.
"""
from fastapi import FastAPI
from .api import router as api_router
from .ui import router as ui_router


app = FastAPI(
    title="Notification Mock",
    description="Mocked notification system for the Upstream SRE agent",
    version="1.0.0",
)

app.include_router(api_router)
app.include_router(ui_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "notification_mock"}
