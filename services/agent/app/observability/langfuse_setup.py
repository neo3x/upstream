"""Langfuse client setup and tracing helpers compatible with SDK v2."""
from __future__ import annotations

from contextlib import nullcontext
from contextvars import ContextVar, Token
from typing import Any

try:
    from langfuse import Langfuse
except Exception:  # pragma: no cover - optional until deps are installed
    Langfuse = None  # type: ignore[assignment]

from ..config import settings


_client: Langfuse | None = None  # type: ignore[valid-type]
_current_observation: ContextVar[Any | None] = ContextVar("langfuse_current_observation", default=None)


def get_langfuse() -> Langfuse | None:  # type: ignore[valid-type]
    """Return the Langfuse client when configured, otherwise None."""
    global _client
    if _client is not None:
        return _client
    if Langfuse is None:
        return None
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        return None

    try:
        _client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
    except Exception:
        _client = None
    return _client


def is_enabled() -> bool:
    return get_langfuse() is not None


def trace_id_for_incident(incident_id: str | None) -> str | None:
    """Use incident_id directly as the trace id for deterministic correlation."""
    if not incident_id or get_langfuse() is None:
        return None
    return incident_id


def _coerce_usage_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    usage_details = kwargs.pop("usage_details", None)
    if usage_details and "usage" not in kwargs:
        prompt_tokens = (
            usage_details.get("prompt_tokens")
            or usage_details.get("input_tokens")
            or usage_details.get("input")
            or 0
        )
        completion_tokens = (
            usage_details.get("completion_tokens")
            or usage_details.get("output_tokens")
            or usage_details.get("output")
            or 0
        )
        total_tokens = usage_details.get("total_tokens")
        if total_tokens is None:
            total_tokens = prompt_tokens + completion_tokens
        kwargs["usage"] = {
            "unit": "TOKENS",
            "input": prompt_tokens,
            "output": completion_tokens,
            "total": total_tokens,
        }
    return kwargs


class _ObservationHandle:
    def __init__(self, observation: Any):
        self._observation = observation
        self._ended = False

    def update(self, **kwargs):
        kwargs = _coerce_usage_kwargs(kwargs)
        if hasattr(self._observation, "update"):
            self._observation.update(**kwargs)
        return self

    def end(self, **kwargs):
        kwargs = _coerce_usage_kwargs(kwargs)
        if hasattr(self._observation, "end"):
            self._observation.end(**kwargs)
        else:
            self.update(**kwargs)
        self._ended = True
        return self

    def __getattr__(self, item: str):
        return getattr(self._observation, item)


class _ObservationContext:
    def __init__(self, handle: _ObservationHandle):
        self._handle = handle
        self._token: Token | None = None

    def __enter__(self):
        self._token = _current_observation.set(self._handle)
        return self._handle

    def __exit__(self, exc_type, exc, tb):
        if self._token is not None:
            _current_observation.reset(self._token)

        if hasattr(self._handle._observation, "end") and not self._handle._ended:
            if exc is not None:
                try:
                    self._handle.end(level="ERROR", status_message=str(exc))
                except Exception:
                    pass
            else:
                try:
                    self._handle.end()
                except Exception:
                    pass
        return False


def start_observation(
    *,
    name: str,
    as_type: str = "span",
    trace_id: str | None = None,
    input: Any = None,
    output: Any = None,
    metadata: Any = None,
    model: str | None = None,
    model_parameters: dict[str, Any] | None = None,
    usage_details: dict[str, int] | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
):
    """Start a Langfuse trace/span/generation when enabled, otherwise no-op."""
    lf = get_langfuse()
    if lf is None:
        return nullcontext(None)

    parent_handle = _current_observation.get()
    parent = getattr(parent_handle, "_observation", parent_handle)

    try:
        if parent is None:
            if as_type == "generation":
                trace = lf.trace(
                    id=trace_id,
                    name=name,
                    user_id=user_id,
                    session_id=session_id,
                    input=input,
                    output=output,
                    metadata=metadata,
                )
                observation = trace.generation(
                    name=name,
                    model=model,
                    model_parameters=model_parameters,
                    input=input,
                    output=output,
                    metadata=metadata,
                    usage=_coerce_usage_kwargs({"usage_details": usage_details}).get("usage"),
                )
            else:
                observation = lf.trace(
                    id=trace_id,
                    name=name,
                    user_id=user_id,
                    session_id=session_id,
                    input=input,
                    output=output,
                    metadata=metadata,
                )
        elif as_type == "generation":
            observation = parent.generation(
                name=name,
                model=model,
                model_parameters=model_parameters,
                input=input,
                output=output,
                metadata=metadata,
                usage=_coerce_usage_kwargs({"usage_details": usage_details}).get("usage"),
            )
        else:
            observation = parent.span(
                name=name,
                input=input,
                output=output,
                metadata=metadata,
            )
    except Exception:
        return nullcontext(None)

    return _ObservationContext(_ObservationHandle(observation))


def propagate_trace_attributes(
    *,
    user_id: str | None = None,
    session_id: str | None = None,
    trace_name: str | None = None,
    metadata: dict[str, str] | None = None,
):
    """Legacy SDK v2 does not expose context propagation; keep API as a no-op."""
    return nullcontext()


def flush_langfuse() -> None:
    lf = get_langfuse()
    if lf is None:
        return
    try:
        lf.flush()
    except Exception:
        return


def get_trace_url(trace_id: str | None) -> str | None:
    if not trace_id or not settings.langfuse_host:
        return None
    base = settings.langfuse_host.rstrip("/")
    return f"{base}/project/upstream-project/traces/{trace_id}"
