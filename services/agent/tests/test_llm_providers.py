"""Quick smoke test script for the configured LLM providers.

Run from the repo root:
    python services/agent/tests/test_llm_providers.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.llm.factory import get_llm_provider  # noqa: E402


def _provider_is_configured(name: str) -> bool:
    if name == "claude":
        return bool(os.getenv("ANTHROPIC_API_KEY"))
    if name == "openai":
        return bool(os.getenv("OPENAI_API_KEY"))
    return True


def run_smoke_test() -> None:
    for name in ["claude", "openai", "ollama"]:
        print(f"\n=== Testing {name} ===")
        if not _provider_is_configured(name):
            print("  SKIPPED: provider is not configured in the current environment")
            continue

        try:
            provider = get_llm_provider(name)
            output = provider.complete_text(
                system="You are a helpful assistant.",
                user="Say 'hello upstream' and nothing else.",
                max_tokens=20,
            )
            print(f"  Output: {output.strip()}")
        except Exception as exc:
            print(f"  FAILED: {exc}")


if __name__ == "__main__":
    run_smoke_test()
