"""Main UI for Upstream."""
from __future__ import annotations

from fastapi import BackgroundTasks, FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import Any, Optional
import httpx
import time
import uuid

from .config import settings


app = FastAPI(title="Upstream UI", version="0.1.0")
APP_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")

_jobs: dict[str, dict[str, Any]] = {}

PROGRESS_STAGES = [
    {
        "key": "guardrails",
        "title": "Running guardrails",
        "detail": "Checking the report, log file, and attachment boundaries before triage starts.",
    },
    {
        "key": "extraction",
        "title": "Extracting symptoms",
        "detail": "Parsing the log stream and pulling out services, codes, and repeated sequences.",
    },
    {
        "key": "retrieval",
        "title": "Searching the codebase",
        "detail": "Finding upstream dependencies and relevant eShop code paths for the incident.",
    },
    {
        "key": "analysis",
        "title": "Forming a hypothesis",
        "detail": "Testing whether the reporter's diagnosis matches the technical evidence.",
    },
    {
        "key": "routing",
        "title": "Creating follow-up",
        "detail": "Preparing the ticket and notification handoff for the owning team.",
    },
]


def _external_links() -> dict[str, str]:
    return {
        "jira": settings.jira_mock_url_external,
        "notifications": settings.notification_mock_url_external,
        "langfuse": settings.langfuse_url_external,
    }


def _provider_label(provider: str) -> str:
    return {
        "claude": "Claude",
        "openai": "OpenAI",
        "ollama": "Ollama",
        "mock": "Mock",
    }.get(provider, provider.title())


def _current_stage_index(job: dict[str, Any]) -> int:
    if job["status"] == "completed":
        return len(PROGRESS_STAGES) - 1
    elapsed = max(0.0, time.monotonic() - job["started_monotonic"])
    return min(int(elapsed // 2.5), len(PROGRESS_STAGES) - 1)


async def _forward_submission(
    job_id: str,
    *,
    text: str,
    reporter_name: str,
    reporter_email: str,
    llm_provider: str,
    log_file_name: str,
    log_file_bytes: bytes,
    log_file_content_type: str | None,
    screenshot_name: str | None,
    screenshot_bytes: bytes | None,
    screenshot_content_type: str | None,
) -> None:
    job = _jobs[job_id]
    job["status"] = "running"

    data = {
        "text": text,
        "reporter_name": reporter_name,
        "reporter_email": reporter_email,
        "llm_provider": llm_provider,
    }
    files: dict[str, tuple[str, bytes, str | None]] = {
        "log_file": (log_file_name, log_file_bytes, log_file_content_type),
    }
    if screenshot_name and screenshot_bytes is not None:
        files["screenshot"] = (screenshot_name, screenshot_bytes, screenshot_content_type)

    try:
        timeout = httpx.Timeout(180.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{settings.agent_url}/incidents",
                data=data,
                files=files,
            )
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:
        job["status"] = "failed"
        job["error"] = str(exc)
        job["finished_monotonic"] = time.monotonic()
        return

    job["status"] = "completed"
    job["result"] = payload
    job["finished_monotonic"] = time.monotonic()


@app.get("/health")
def health():
    return {"status": "ok", "service": "upstream-ui"}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "external_links": _external_links(),
        },
    )


@app.post("/submit", response_class=HTMLResponse)
async def submit(
    request: Request,
    background_tasks: BackgroundTasks,
    text: str = Form(...),
    reporter_name: str = Form("anonymous"),
    reporter_email: str = Form("anonymous@example.com"),
    llm_provider: str = Form("claude"),
    log_file: UploadFile = File(...),
    screenshot: Optional[UploadFile] = File(None),
):
    job_id = uuid.uuid4().hex[:12]
    log_file_bytes = await log_file.read()
    screenshot_bytes = None
    screenshot_name = None
    screenshot_content_type = None

    if screenshot and screenshot.filename:
        screenshot_bytes = await screenshot.read()
        screenshot_name = screenshot.filename
        screenshot_content_type = screenshot.content_type

    _jobs[job_id] = {
        "id": job_id,
        "provider": llm_provider,
        "status": "queued",
        "result": None,
        "error": None,
        "created_monotonic": time.monotonic(),
        "started_monotonic": time.monotonic(),
        "finished_monotonic": None,
    }

    background_tasks.add_task(
        _forward_submission,
        job_id,
        text=text,
        reporter_name=reporter_name,
        reporter_email=reporter_email,
        llm_provider=llm_provider,
        log_file_name=log_file.filename,
        log_file_bytes=log_file_bytes,
        log_file_content_type=log_file.content_type,
        screenshot_name=screenshot_name,
        screenshot_bytes=screenshot_bytes,
        screenshot_content_type=screenshot_content_type,
    )

    return templates.TemplateResponse(
        request,
        "partials/progress.html",
        {
            "job_id": job_id,
            "provider_label": _provider_label(llm_provider),
            "stage_index": 0,
            "stages": PROGRESS_STAGES,
        },
    )


@app.get("/submission-status/{job_id}", response_class=HTMLResponse)
async def submission_status(request: Request, job_id: str):
    job = _jobs.get(job_id)
    if not job:
        return templates.TemplateResponse(
            request,
            "partials/error.html",
            {
                "error": "Submission not found. Refresh the page and try again.",
            },
        )

    if job["status"] == "failed":
        return templates.TemplateResponse(
            request,
            "partials/error.html",
            {
                "error": job["error"] or "The UI could not reach the agent service.",
            },
        )

    if job["status"] == "completed":
        return templates.TemplateResponse(
            request,
            "partials/result.html",
            {
                "result": job["result"],
                "external_links": {
                    "jira": settings.jira_mock_url_external,
                    "notifications": settings.notification_mock_url_external,
                },
            },
        )

    return templates.TemplateResponse(
        request,
        "partials/progress.html",
        {
            "job_id": job_id,
            "provider_label": _provider_label(job["provider"]),
            "stage_index": _current_stage_index(job),
            "stages": PROGRESS_STAGES,
        },
    )


@app.get("/provider-info/{provider}", response_class=HTMLResponse)
async def provider_info(request: Request, provider: str):
    return templates.TemplateResponse(
        request,
        "partials/provider_info.html",
        {
            "provider": provider,
        },
    )
