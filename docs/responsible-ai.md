# Responsible AI in Upstream

Upstream is an incident-triage agent,
not an autonomous operator.
Its job is to improve the quality of the first triage package by reading the
reporter's evidence,
checking that evidence against code context,
and creating a more useful handoff for the likely owning team.

Because the product is explicitly allowed to disagree with a human reporter,
responsible AI is a core product requirement rather than a later compliance
layer.

The AgentX assignment calls out five Responsible AI principles.
This document explains how Upstream addresses each one,
where the current design is intentionally limited,
and what trade-offs remain.

## Fairness

Upstream does not rank,
score,
or prioritize people.
It triages technical incidents.
There are no protected attributes,
user reputation scores,
or behavioral profiles in the decision path.

The agent's reasoning is grounded in technical evidence:

- reporter text
- uploaded logs
- optional screenshot
- retrieved code references from the eShop snapshot

That means a junior support engineer and a senior SRE receive the same analysis
logic.
The reporter's identity is used only for routing notifications and trace/user
association,
not for changing the diagnosis.

**Known limitation**

Fairness here is narrower than in consumer-facing AI systems.
The system still inherits the usual LLM risks around inconsistent phrasing or
model variability,
especially when evidence is incomplete.
Upstream reduces that risk through structured outputs,
low-temperature prompting,
and evidence citations,
but it does not eliminate it entirely.

## Transparency

Transparency is one of the product's strongest properties.
Upstream is designed to show its reasoning path rather than only a verdict.

Current transparency features include:

- explicit `agrees_with_reporter` output
- cited reasoning grounded in logs and code excerpts
- visible provider choice in the submission UI
- a prominent warning when the user selects Ollama
- versioned prompts stored in the repository
- observability evidence via structured logs and Langfuse traces

In practice,
the user sees not only the final diagnosis,
but also whether the agent thinks the original diagnosis was mistaken and which
upstream dependency likely explains the symptom.

**What we do not claim**

We do not claim that the model exposes its full internal reasoning.
Instead,
we claim something narrower and verifiable:
the agent produces a concise evidence trail that a human can inspect.

## Accountability

Every incident receives a stable `incident_id` at intake.
That same identifier is propagated through:

- structured logs
- Langfuse traces
- Jira mock tickets
- notification records
- the ticket-resolution webhook path

This gives the project a concrete audit trail from submission to resolution.

Accountability also shows up in the output contract:

- the agent must name the suspected root service
- it must state whether it agrees or disagrees with the reporter
- it must provide reasoning
- it must provide a confidence score
- when confidence is low, it should remain cautious rather than invent certainty

Rejected malicious inputs are also auditable.
Guardrail-triggered rejections create:

- warning log entries
- a security alert in the notification mock
- a security review ticket in the Jira mock

That makes the safety system inspectable rather than invisible.

## Privacy

Incident payloads may contain sensitive operational data.
Upstream addresses that risk in several ways.

### Data handling choices

- API keys are loaded from environment variables only
- `.env.example` contains placeholders, never real secrets
- no credentials are committed to the repository
- user payloads are processed in memory inside the request path
- persisted demo state is limited to LangGraph checkpoint data and mock-service records

### Provider choice as a privacy control

Upstream supports three providers because privacy requirements differ by team:

- **Claude** for strongest reasoning quality in hosted deployments
- **OpenAI** as an alternative hosted path
- **Ollama** for local or air-gapped deployments where data must remain on infrastructure controlled by the operator

The UI is intentionally honest about this trade-off:
Ollama improves data locality,
but local models typically provide weaker reasoning quality than frontier cloud
models.

### Self-hosted observability

Langfuse is deployed self-hosted in this project.
That means prompt and trace data remain under the operator's control rather than
being sent to a third-party SaaS observability platform.

**Known limitation**

If the user selects a hosted provider,
incident text and logs are still sent to that provider for inference.
Upstream is transparent about that by exposing provider selection at submission
time instead of hiding it.

## Security

Security is implemented as a layered defense,
not a single prompt instruction.

### 1. Input validation

The guardrail layer validates:

- maximum text length
- maximum log file size
- maximum image size
- UTF-8 decodability
- image MIME type and magic bytes
- suspicious binary uploads
- empty or unstructured logs

### 2. Prompt injection detection

Both the reporter text and the uploaded log contents are scanned for known
prompt injection patterns such as:

- `ignore previous instructions`
- `you are now`
- `reveal your system prompt`
- fake system-message syntax
- suspicious directive text embedded in logs

### 3. Hardened prompts

All untrusted content is wrapped inside explicit delimiters such as
`===REPORT START===` and `===LOG START===`.
The system prompt instructs the model to treat those blocks as data only,
never as instructions.

### 4. Tool-use safety

The agent does not expose arbitrary tools to the model.
Its outbound actions are fixed internal integrations:

- create a Jira mock ticket
- send a notification
- handle a resolution webhook

That sharply limits the blast radius of a successful prompt injection attempt.

### 5. Visible audit trail

Rejected malicious submissions generate visible security artifacts,
which are documented with evidence in `AGENTS_USE.md`:

- rejection response
- structured warning logs
- security alert notification
- security review ticket

## Human Oversight and Product Scope

Upstream is a triage assistant,
not a replacement for responders.
Humans still decide whether to accept the diagnosis,
how to remediate the incident,
and whether to override the routing.

This matters most in ambiguous cases:
if the evidence is incomplete,
the product should help humans think more clearly,
not pretend to own the final operational decision.

## Known Limitations

- Prompt quality still affects consistency, especially on “absence of evidence” scenarios.
- Ollama can degrade structured-output reliability under heavier load.
- The project does not yet include automated prompt-evaluation benchmarking across providers.
- The current design treats each incident independently; it does not yet deduplicate related reports.

These are acceptable limitations for the current hackathon scope,
but they would be important follow-up work before a production rollout.
