# Responsible AI Notes

## Why Responsible AI Matters Here

Upstream is allowed to disagree with a human reporter.
That makes Responsible AI a product requirement,
not a branding exercise.
If the system routes work to the wrong team confidently,
it can waste time and reduce trust.
If it handles sensitive logs carelessly,
it can create privacy risk.

## Grounding Policy

The core grounding rule is simple:
important claims should point back to evidence.
For Upstream,
that evidence comes from:

- the reporter's text
- uploaded logs
- the optional screenshot
- retrieved code context from the eShop snapshot

The goal is to minimize unsupported reasoning and make disagreement auditable.

## Provider Choice

Upstream supports three provider paths because different environments have
different privacy and compliance constraints.

- **Claude** is the recommended default because the project depends on strong
  contradiction-aware reasoning.
- **OpenAI** is a hosted alternative for teams that prefer that ecosystem.
- **Ollama** is the privacy-first option for local or air-gapped deployments.

The trade-off is explicit:
more privacy does not automatically mean better triage quality.

## Guardrails

The system is designed to validate payloads before the main reasoning flow.
This includes:

- file and payload validation
- prompt injection detection
- early rejection or rerouting of unsafe inputs
- constrained downstream tool calls

The prompt injection scenario is one of the three core demos because safe
refusal is part of the product's value.

## Human Oversight

Upstream is meant to improve the quality of the first triage package,
not to replace responders.
A human can still review the ticket,
inspect the cited evidence,
and disagree with the agent if needed.
This is especially important in ambiguous cases where the evidence is incomplete.

## Data Handling

The project supports both hosted and local model paths.
That matters because incident payloads may contain sensitive operational data.
Organizations that cannot send logs to a hosted provider can use Ollama,
accepting the reasoning-quality trade-off in exchange for data sovereignty.

## What Will Be Added Later

Runtime evidence for this document will be added in Phase 13.
That will include:

- trace screenshots
- guardrail rejection examples
- structured log samples with correlation IDs
