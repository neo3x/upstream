"""Anthropic Claude provider."""
import json

from anthropic import Anthropic

from ..config import settings
from ..observability.langfuse_setup import start_observation
from .base import LLMProvider


def _extract_json_payload(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        parts = stripped.split("```")
        if len(parts) >= 2:
            stripped = parts[1].strip()
            if stripped.startswith("json"):
                stripped = stripped[4:].strip()

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and end > start:
        return stripped[start:end + 1]
    return stripped


class ClaudeProvider(LLMProvider):
    name = "claude"
    supports_vision = True

    def __init__(self):
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.model = "claude-sonnet-4-5"

    def complete_text(self, system, user, max_tokens=1024, temperature=0.2):
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(
            block.text for block in resp.content if getattr(block, "type", "") == "text"
        ).strip()

    def complete_multimodal(
        self,
        system,
        user_text,
        image_b64,
        max_tokens=1024,
        temperature=0.2,
    ):
        content = [{"type": "text", "text": user_text}]
        if image_b64:
            content.insert(0, {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": image_b64,
                },
            })
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": content}],
        )
        return "".join(
            block.text for block in resp.content if getattr(block, "type", "") == "text"
        ).strip()

    def complete_structured(
        self,
        system,
        user,
        schema,
        image_b64=None,
        max_tokens=2048,
        temperature=0.2,
    ):
        schema_json = schema.model_json_schema()
        instruction = (
            "\n\nReturn your response as valid JSON matching this schema:\n"
            f"```json\n{json.dumps(schema_json, indent=2)}\n```\n"
            "Return ONLY the JSON object. No prose before or after."
        )
        content = [{"type": "text", "text": user}]
        if image_b64:
            content.insert(0, {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": image_b64,
                },
            })

        with start_observation(
            name="claude.complete_structured",
            as_type="generation",
            model=self.model,
            input={"system": system[:500], "user": user[:1000]},
            metadata={"schema": schema.__name__},
            model_parameters={
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
        ) as generation:
            resp = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system + instruction,
                messages=[{"role": "user", "content": content}],
            )
            text = "".join(
                block.text for block in resp.content if getattr(block, "type", "") == "text"
            ).strip()
            cleaned = _extract_json_payload(text)
            try:
                result = schema.model_validate_json(cleaned)
            except Exception as exc:
                if generation is not None:
                    generation.update(level="ERROR", status_message=str(exc), output={"raw": cleaned[:500]})
                raise

            if generation is not None:
                generation.update(
                    output={"parsed": True, "schema": schema.__name__},
                    usage_details={
                        "prompt_tokens": getattr(resp.usage, "input_tokens", 0) or 0,
                        "completion_tokens": getattr(resp.usage, "output_tokens", 0) or 0,
                    },
                )
            return result
