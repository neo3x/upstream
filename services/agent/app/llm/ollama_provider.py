"""Ollama provider for offline or privacy-sensitive deployments."""
import json

import ollama

from ..config import settings
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


def _validate_structured_output(schema, cleaned: str):
    try:
        return schema.model_validate_json(cleaned)
    except Exception as exc:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            for wrapper_key in ("properties", "result", "output", "data"):
                nested = parsed.get(wrapper_key)
                if isinstance(nested, dict):
                    try:
                        return schema.model_validate(nested)
                    except Exception:
                        pass
        raise exc


class OllamaProvider(LLMProvider):
    name = "ollama"
    supports_vision = False

    def __init__(self):
        self.client = ollama.Client(host=settings.ollama_base_url)
        self.model = settings.ollama_model
        try:
            self.client.show(self.model)
        except Exception:
            self.client.pull(self.model)

    def complete_text(self, system, user, max_tokens=1024, temperature=0.2):
        resp = self.client.chat(
            model=self.model,
            options={"num_predict": max_tokens, "temperature": temperature},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return resp["message"]["content"].strip()

    def complete_multimodal(
        self,
        system,
        user_text,
        image_b64,
        max_tokens=1024,
        temperature=0.2,
    ):
        if image_b64 and not self.supports_vision:
            return self.complete_text(
                system=system,
                user=(
                    user_text
                    + "\n\n[An image was attached but this Ollama model is text-only.]"
                ),
                max_tokens=max_tokens,
                temperature=temperature,
            )
        return self.complete_text(system, user_text, max_tokens, temperature)

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
            "\n\nYou MUST respond with ONLY a valid JSON object matching this schema:\n"
            f"```json\n{json.dumps(schema_json, indent=2)}\n```\n"
            "No prose, no markdown, no code fences. Just the JSON object.\n"
            "Do NOT return the JSON schema itself. Do NOT wrap the answer inside keys like "
            "'properties', 'result', 'output', or 'data'."
        )
        prompt_user = user
        last_text = ""

        for attempt in range(2):
            last_text = self.complete_multimodal(
                system=system + instruction,
                user_text=prompt_user,
                image_b64=image_b64,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            cleaned = _extract_json_payload(last_text)
            try:
                return _validate_structured_output(schema, cleaned)
            except Exception as exc:
                if attempt == 1:
                    raise ValueError(
                        f"Ollama returned invalid JSON for schema {schema.__name__}: {exc}. "
                        f"Raw: {cleaned[:500]}"
                    ) from exc
                prompt_user = (
                    f"{user}\n\nYour previous response was invalid JSON:\n{cleaned}\n\n"
                    "Try again and return only the final JSON object that matches the schema exactly. "
                    "Do not return schema metadata or wrap the object inside another object."
                )
