"""Run the demo scenarios through the prompt-sensitive nodes.

This is a lightweight local regression harness for Phase 8. It avoids the full
API/container stack and focuses on the outputs that are most sensitive to prompt
quality: guardrails, extraction, causal analysis, and severity.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.graph.nodes.causal_analysis import causal_analysis_node
from app.graph.nodes.extraction import extraction_node
from app.graph.nodes.guardrails import guardrails_node
from app.graph.nodes.severity import severity_node


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
REPO_ROOT = Path(__file__).resolve().parents[3]

SCENARIOS = {
    "scenario_1_identity": {
        "text": FIXTURES_DIR / "scenario_1_identity.txt",
        "log": FIXTURES_DIR / "scenario_1_identity.log",
        "reporter_name": "Alice",
        "reporter_email": "alice@example.com",
    },
    "scenario_2_eventbus": {
        "text": FIXTURES_DIR / "scenario_2_eventbus.txt",
        "log": FIXTURES_DIR / "scenario_2_eventbus.log",
        "reporter_name": "Bob Support",
        "reporter_email": "bob@example.com",
    },
    "scenario_3_injection": {
        "text": FIXTURES_DIR / "scenario_3_injection.txt",
        "log": FIXTURES_DIR / "scenario_3_injection.log",
        "reporter_name": "Mallory",
        "reporter_email": "mallory@example.com",
    },
}


def _load_state(name: str, provider: str) -> dict:
    scenario = SCENARIOS[name]
    return {
        "incident_id": f"{name}-local",
        "raw_text": scenario["text"].read_text(encoding="utf-8"),
        "log_content": scenario["log"].read_text(encoding="utf-8"),
        "reporter_name": scenario["reporter_name"],
        "reporter_email": scenario["reporter_email"],
        "llm_provider": provider,
        "errors": [],
    }


def _run_scenario(name: str, provider: str) -> dict:
    state = _load_state(name, provider)
    state.update(guardrails_node(state))

    if not state.get("guardrails_passed"):
        return {
            "scenario": name,
            "status": "rejected",
            "guardrails_reason": state.get("guardrails_reason"),
            "errors": state.get("errors", []),
        }

    state.update(extraction_node(state))
    state.update(causal_analysis_node(state))
    state.update(severity_node(state))

    return {
        "scenario": name,
        "status": "processed",
        "extracted": state["extracted"].model_dump(),
        "hypothesis": state["hypothesis"].model_dump(),
        "severity": state["severity"].model_dump(),
        "errors": state.get("errors", []),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--provider",
        default="mock",
        help="LLM provider name, e.g. claude | openai | ollama | mock",
    )
    parser.add_argument(
        "--scenario",
        choices=[*SCENARIOS.keys(), "all"],
        default="all",
        help="Scenario to run",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="How many times to run each selected scenario",
    )
    parser.add_argument(
        "--save-dir",
        type=Path,
        default=None,
        help="Optional directory for saving JSON outputs",
    )
    args = parser.parse_args()

    scenario_names = list(SCENARIOS) if args.scenario == "all" else [args.scenario]
    save_dir = None
    if args.save_dir:
        save_dir = args.save_dir
        if not save_dir.is_absolute():
            save_dir = REPO_ROOT / save_dir
        save_dir.mkdir(parents=True, exist_ok=True)

    for scenario_name in scenario_names:
        for run_index in range(1, args.repeat + 1):
            result = _run_scenario(scenario_name, args.provider)
            print(json.dumps(result, indent=2))
            if save_dir:
                output_path = save_dir / f"{scenario_name}_run_{run_index}.json"
                output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
