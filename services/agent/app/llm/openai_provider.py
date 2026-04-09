"""OpenAI provider."""
import json

from openai import OpenAI

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


class OpenAIProvider(LLMProvider):
    name = "openai"
    supports_vision = True

    def __init__(self):
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = "gpt-4o"

    def complete_text(self, system, user, max_tokens=1024, temperature=0.2):
        resp = self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return (resp.choices[0].message.content or "").strip()

    def complete_multimodal(
        self,
        system,
        user_text,
        image_b64,
        max_tokens=1024,
        temperature=0.2,
    ):
        user_content = [{"type": "text", "text": user_text}]
        if image_b64:
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{image_b64}"},
            })
        resp = self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
        )
        return (resp.choices[0].message.content or "").strip()

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
            "\n\nReturn JSON matching this schema:\n"
            f"```json\n{json.dumps(schema_json, indent=2)}\n```"
        )
        user_content = [{"type": "text", "text": user + instruction}]
        if image_b64:
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{image_b64}"},
            })
        with start_observation(
            name="openai.complete_structured",
            as_type="generation",
            model=self.model,
            input={"system": system[:500], "user": user[:1000]},
            metadata={"schema": schema.__name__},
            model_parameters={
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
        ) as generation:
            resp = self.client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_content},
                ],
            )
            cleaned = _extract_json_payload(resp.choices[0].message.content or "")
            try:
                result = schema.model_validate_json(cleaned)
            except Exception as exc:
                if generation is not None:
                    generation.update(level="ERROR", status_message=str(exc), output={"raw": cleaned[:500]})
                raise

            usage = resp.usage
            if generation is not None:
                generation.update(
                    output={"parsed": True, "schema": schema.__name__},
                    usage_details={
                        "prompt_tokens": getattr(usage, "prompt_tokens", 0) or 0,
                        "completion_tokens": getattr(usage, "completion_tokens", 0) or 0,
                        "total_tokens": getattr(usage, "total_tokens", 0) or 0,
                    },
                )
            return result
