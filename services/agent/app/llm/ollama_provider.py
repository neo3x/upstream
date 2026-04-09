"""Ollama provider for offline or privacy-sensitive deployments."""
import json

import ollama

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


def _validate_structured_output(schema, cleaned: str):
    try:
        return schema.model_validate_json(cleaned)
    except Exception as exc:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            normalized = _normalize_candidate(schema, parsed)
            try:
                return schema.model_validate(normalized)
            except Exception:
                pass
            for wrapper_key in ("properties", "result", "output", "data"):
                nested = parsed.get(wrapper_key)
                if isinstance(nested, dict):
                    try:
                        return schema.model_validate(_normalize_candidate(schema, nested))
                    except Exception:
                        pass
        raise exc


def _normalize_candidate(schema, candidate: dict) -> dict:
    normalized = dict(candidate)
    nested_properties = normalized.get("properties")
    if isinstance(nested_properties, dict):
        for field_name in schema.model_fields:
            normalized.setdefault(field_name, nested_properties.get(field_name))

    for field_name, field_info in schema.model_fields.items():
        value = normalized.get(field_name)
        if value is None:
            continue

        if isinstance(value, list):
            annotation = str(field_info.annotation)
            if "list[str]" in annotation.lower():
                normalized[field_name] = [str(item) for item in value]
        elif isinstance(value, (int, float)) and field_info.annotation is str:
            normalized[field_name] = str(value)

    return normalized


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

    def _chat(self, *, system: str, user: str, max_tokens: int, temperature: float):
        return self.client.chat(
            model=self.model,
            options={"num_predict": max_tokens, "temperature": temperature},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )

    def complete_text(self, system, user, max_tokens=1024, temperature=0.2):
        resp = self._chat(system=system, user=user, max_tokens=max_tokens, temperature=temperature)
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
        last_error = None

        with start_observation(
            name="ollama.complete_structured",
            as_type="generation",
            model=self.model,
            input={"system": system[:500], "user": user[:1000]},
            metadata={"schema": schema.__name__},
            model_parameters={"max_tokens": max_tokens, "temperature": temperature},
        ) as generation:
            for attempt in range(2):
                request_user = prompt_user
                if image_b64 and not self.supports_vision:
                    request_user = (
                        prompt_user
                        + "\n\n[An image was attached but this Ollama model is text-only.]"
                    )
                resp = self._chat(
                    system=system + instruction,
                    user=request_user,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                last_text = resp["message"]["content"].strip()
                cleaned = _extract_json_payload(last_text)
                try:
                    result = _validate_structured_output(schema, cleaned)
                    if generation is not None:
                        generation.update(
                            output={"parsed": True, "schema": schema.__name__},
                            usage_details={
                                "prompt_tokens": resp.get("prompt_eval_count", 0) or 0,
                                "completion_tokens": resp.get("eval_count", 0) or 0,
                            },
                        )
                    return result
                except Exception as exc:
                    last_error = exc
                    if attempt == 1:
                        break
                    prompt_user = (
                        f"{user}\n\nYour previous response was invalid JSON:\n{cleaned}\n\n"
                        "Try again and return only the final JSON object that matches the schema exactly. "
                        "Do not return schema metadata or wrap the object inside another object."
                    )

            repaired_resp = self._chat(
                system=(
                    "You repair malformed JSON. Return only a corrected JSON object that matches the "
                    "requested schema exactly."
                ),
                user=(
                    f"Schema:\n{json.dumps(schema_json, indent=2)}\n\n"
                    f"Malformed JSON:\n{_extract_json_payload(last_text)}\n\n"
                    "Return the repaired JSON object only."
                ),
                max_tokens=max_tokens,
                temperature=0.0,
            )
            cleaned = _extract_json_payload(repaired_resp["message"]["content"].strip())
            try:
                result = _validate_structured_output(schema, cleaned)
            except Exception as exc:
                root_error = last_error or exc
                if generation is not None:
                    generation.update(level="ERROR", status_message=str(root_error), output={"raw": cleaned[:500]})
                raise ValueError(
                    f"Ollama returned invalid JSON for schema {schema.__name__}: {root_error}. "
                    f"Raw: {cleaned[:500]}"
                ) from exc

            if generation is not None:
                generation.update(
                    output={"parsed": True, "schema": schema.__name__, "repaired": True},
                    usage_details={
                        "prompt_tokens": repaired_resp.get("prompt_eval_count", 0) or 0,
                        "completion_tokens": repaired_resp.get("eval_count", 0) or 0,
                    },
                )
            return result
