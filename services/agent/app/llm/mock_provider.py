"""Mock provider used for tests and no-key local development."""
from typing import Any, get_args, get_origin

from pydantic import BaseModel

from .base import LLMProvider


def _placeholder_for_annotation(annotation: Any) -> Any:
    origin = get_origin(annotation)
    args = [arg for arg in get_args(annotation) if arg is not type(None)]

    if origin in (list, set, tuple, frozenset):
        return []
    if origin is dict:
        return {}
    if args:
        return _placeholder_for_annotation(args[0])

    if isinstance(annotation, type):
        if issubclass(annotation, BaseModel):
            return _placeholder_payload_for_schema(annotation)
        if annotation is str:
            return "[mock]"
        if annotation is int:
            return 0
        if annotation is float:
            return 0.0
        if annotation is bool:
            return False
    return None


def _placeholder_payload_for_schema(schema: type[BaseModel]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for field_name, field_info in schema.model_fields.items():
        if field_info.is_required():
            payload[field_name] = _placeholder_for_annotation(field_info.annotation)
    return payload


class MockProvider(LLMProvider):
    name = "mock"
    supports_vision = True

    def complete_text(self, system, user, max_tokens=1024, temperature=0.2):
        return "[mock] text response"

    def complete_multimodal(
        self,
        system,
        user_text,
        image_b64,
        max_tokens=1024,
        temperature=0.2,
    ):
        return "[mock] multimodal response"

    def complete_structured(
        self,
        system,
        user,
        schema,
        image_b64=None,
        max_tokens=2048,
        temperature=0.2,
    ):
        return schema.model_validate(_placeholder_payload_for_schema(schema))

