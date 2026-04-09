# AGENTS_USE.md

This document follows the AgentX Hackathon agent write-up structure for Upstream.
It explains what the agent does,
how the graph is organized,
how context is engineered,
and how the system is intended to scale and defend itself.
Sections that require runtime screenshots or live trace evidence are clearly
marked and will be completed in Phase 13.

## 1. Agent Overview

**Agent name:** Upstream

**Purpose**

Upstream is a multimodal SRE intake and triage agent for e-commerce incidents.
Its defining behavior is that it does not automatically trust the reporter's
diagnosis.
Instead of treating the incident submission as a directive,
Upstream treats it as a hypothesis.
It discusses the incident with evidence:
text from the reporter,
uploaded logs,
an optional screenshot,
and retrieved source-code context from a curated subset of `dotnet/eShop`.
The output is not only a summary of what the reporter said.
It is an evidence-backed recommendation about what is actually wrong,
who should own the ticket,
and why.

**Primary outcome**

Reduce misrouting during the first minute of an incident by producing a grounded
triage package before the issue is handed to a team.

**Tech stack**

| Category | Choice |
| --- | --- |
| Language | Python 3.11 |
| API framework | FastAPI |
| Agent orchestration | LangGraph |
| LLM providers | Claude (recommended), OpenAI, Ollama |
| Vector retrieval | Qdrant |
| Observability | Langfuse |
| Logging | structlog |
| UI stack | FastAPI + Jinja2 + HTMX + Tailwind |
| Local orchestration | Docker Compose |

## 2. Agents & Capabilities

Upstream is implemented as a primary LangGraph workflow with multiple focused
nodes that behave like sub-agents.
Each node has a narrow responsibility,
explicit inputs and outputs,
and a predictable handoff to the next stage.

### Guardrails Agent

| Field | Value |
| --- | --- |
| Role | Validate inputs, detect prompt injection, reject unsafe or malformed payloads before expensive analysis begins |
| Type | Deterministic validation node with targeted model-assisted security checks |
| LLM | Optional lightweight classifier call when heuristic checks are inconclusive |
| Inputs | Reporter text, uploaded log metadata, optional image metadata, request headers, allowed file constraints |
| Outputs | Validation result, rejection reason if blocked, sanitized incident payload if accepted |
| Tools | Input schema validation, MIME/type checks, size limits, prompt-injection detector, allow/deny routing rules |

### Extraction Agent

| Field | Value |
| --- | --- |
| Role | Convert raw multimodal input into a structured symptom record |
| Type | Multimodal reasoning node |
| LLM | Claude / OpenAI multimodal path, or Ollama-compatible local fallback |
| Inputs | Reporter text, raw log file content, optional screenshot, validated request metadata |
| Outputs | Structured symptoms, normalized entities, candidate services, extracted error messages, uncertainty notes |
| Tools | Log parser, text normalizer, image-aware prompt, schema-constrained extraction prompt |

### Causal Analysis Agent

| Field | Value |
| --- | --- |
| Role | Form the core causal hypothesis and decide whether the reporter's diagnosis is supported or contradicted |
| Type | Retrieval-augmented reasoning node |
| LLM | Claude Sonnet recommended; OpenAI and Ollama supported through the same provider abstraction |
| Inputs | Structured symptoms, retrieved eShop code chunks, reporter hypothesis, relevant log excerpts, optional image cues |
| Outputs | Root-cause hypothesis, owning service/team recommendation, supporting evidence references, counter-hypothesis analysis |
| Tools | Qdrant semantic retrieval, code chunk formatter, grounding prompt, evidence-ranking logic |

### Severity Agent

| Field | Value |
| --- | --- |
| Role | Estimate incident priority and probable blast radius |
| Type | Reasoning + rules hybrid node |
| LLM | Same provider path as the main graph, usually smaller prompt budget than causal analysis |
| Inputs | Structured symptoms, inferred root cause, affected flows, user-facing impact cues from logs and screenshot |
| Outputs | Suggested priority, blast-radius summary, escalation rationale |
| Tools | Priority rubric, impact heuristics, optional model-assisted severity explanation |

### Ticket Creation Agent

| Field | Value |
| --- | --- |
| Role | Create a structured issue in the Jira mock with all evidence needed for human follow-up |
| Type | Tool-calling integration node |
| LLM | None required for the write operation; formatting may use deterministic templates |
| Inputs | Incident summary, causal analysis result, severity result, evidence references |
| Outputs | Ticket payload, created ticket ID, persistence confirmation |
| Tools | Jira mock HTTP client, response validation, deterministic ticket template |

### Notification Agent

| Field | Value |
| --- | --- |
| Role | Notify the assigned team that a new incident has been routed to them |
| Type | Tool-calling integration node |
| LLM | None required for transport; optional summary templating can be deterministic |
| Inputs | Ticket ID, responsible team, short assignment explanation, severity |
| Outputs | Notification payload, delivery confirmation |
| Tools | Notification mock HTTP client, message template, retry-safe delivery wrapper |

### Resolution Agent

| Field | Value |
| --- | --- |
| Role | Handle post-resolution webhook events and notify the original reporter about what was actually fixed |
| Type | Separate small LangGraph workflow triggered by webhook |
| LLM | Small summarization call or deterministic template depending on final implementation choice |
| Inputs | Ticket resolution event, final ticket summary, original incident context |
| Outputs | Reporter-facing resolution summary, notification delivery record |
| Tools | Jira mock webhook handler, notification mock client, resolution summary template |

### Capability summary

Across these nodes,
Upstream supports:

- multimodal intake
- input validation and injection defense
- retrieval-augmented causal reasoning
- priority estimation
- ticketing handoff
- team notification
- post-resolution communication

The most important capability is not generic summarization.
It is the ability to disagree with the reporter responsibly and explain why.

## 3. Architecture & Orchestration

![Architecture](docs/architecture-diagram.png)
_Diagram placeholder: the final architecture PNG will be generated in Phase 5._

### System design

Upstream uses a monorepo layout with separate services for the UI,
agent runtime,
Jira mock,
and notification mock.
The agent service contains the LangGraph flows,
provider abstractions,
retrieval adapters,
guardrails,
and observability hooks.
Qdrant stores the indexed code embeddings for the curated eShop snapshot.
Langfuse captures trace-level visibility into model calls,
latency,
and step sequencing.

### Orchestration approach

The primary incident graph is sequential by default,
with conditional routing around the guardrails stage and the error-handling path.
The nominal flow is:

1. `guardrails`
2. `extraction`
3. `retrieval`
4. `causal_analysis`
5. `severity`
6. `ticket_creation`
7. `notification`
8. `finalize`

If the guardrails node rejects the input,
execution stops early and routes to a safe rejection outcome.
If a downstream node raises an error or returns invalid state,
the graph routes to a fallback `error_handling` node that records the failure
and generates a controlled response.

### State management

State is represented as a `TypedDict`-style graph state.
Each node reads the subset it needs and returns a state delta.
LangGraph merges those deltas automatically.
Persistence is handled through a SQLite-backed LangGraph checkpointer during the
initial implementation.
This is a practical choice for a single-instance hackathon deployment and makes
replay/debugging straightforward.

The current state shape is expected to include:

- request metadata
- validated input references
- extracted symptom schema
- retrieved code chunks
- causal hypothesis
- severity output
- ticket metadata
- notification metadata
- error details
- correlation identifiers

### Handoff logic

Every node is designed to hand off explicit structured data rather than prose.
That keeps later nodes grounded and makes the graph auditable.
Examples:

- Guardrails hands off a sanitized payload and safety decision.
- Extraction hands off structured symptoms and normalized evidence snippets.
- Retrieval hands off ranked code chunks.
- Causal analysis hands off a root-cause hypothesis plus references.
- Severity hands off priority and blast-radius metadata.
- Ticket creation hands off the created ticket ID and payload.

### Error handling

Each node is expected to wrap risky operations in `try/except` handling and
update the graph state with structured error information.
The graph-level fallback edge routes those failures to a final
`error_handling` node.
That node is responsible for:

- preserving the correlation ID
- capturing enough context for debugging
- emitting a structured failure event
- returning a user-safe response instead of a raw exception

### Service boundaries

The architecture is intentionally explicit about what belongs where:

- The UI collects incidents and displays status.
- The agent service performs reasoning and orchestration.
- Qdrant serves retrieval.
- Langfuse provides observability.
- The mocks emulate downstream operational systems.

That separation matters because the demo is intended to show not only a model
call,
but an operational handoff workflow.

## 4. Context Engineering

### Context sources

Upstream combines four context sources:

1. The reporter's free-form text description.
2. The uploaded log file.
3. The optional screenshot.
4. Retrieved chunks from the indexed eShop snapshot in Qdrant.

The graph does not treat these sources as equal.
Reporter text is valuable but potentially biased.
Logs are noisy but often concrete.
Screenshots add UI or monitoring clues.
Retrieved code gives the agent architectural memory about what the system can
and cannot plausibly be doing.

### Retrieval strategy

The eShop snapshot is indexed into Qdrant during Docker build time so technical
context is ready when the stack starts.
At triage time,
the system performs semantic search against relevant code chunks
using symptoms extracted from the logs and reporter text.
The retrieved chunks are then passed to the causal analysis node together with
the most relevant log fragments.

This design keeps the reasoning step grounded in the actual structure of the
target system rather than in generic e-commerce priors.

### Token management

Upstream is designed to manage prompt size deliberately:

- only top-k retrieved code chunks are included
- long logs are summarized before full-context prompting
- repeated boilerplate log lines are de-emphasized
- screenshots are optional rather than mandatory
- node prompts focus on the minimum evidence required for the current decision

That keeps the expensive reasoning budget focused on causal interpretation,
not on shoveling raw input into a single oversized prompt.

### Grounding rules

The core grounding requirement is strict:
every important claim in the agent's hypothesis must point back to evidence.
That evidence should resolve to either:

- a specific log line or log pattern
- a specific file / line reference from the eShop snapshot
- a directly observable cue from the screenshot

The prompt instructions enforce this constraint explicitly.
The goal is not just better answers.
The goal is auditable answers.

### Context filtering philosophy

Upstream prefers omission over contamination.
If a chunk of context is weakly relevant,
it should not be included just because it fits into the token window.
This matters most when the reporter has already proposed a diagnosis.
The system has to resist being overly anchored by the user's framing.
Context engineering is therefore partly about retrieval quality
and partly about bias control.

### Why this matters for the product

The promise of Upstream is not,
"we added RAG."
The promise is,
"we use the right evidence to challenge the first explanation."
That makes context engineering central to the product,
not a hidden infrastructure detail.

## 5. Use Cases

### Use Case 1 — Identity cascade

**Scenario**

The reporter claims Ordering is broken because checkout requests are failing.
The visible symptom appears in the ordering path,
so the first human instinct is to route the incident to the Ordering team.

**How Upstream handles it**

1. Guardrails validate the submission.
2. Extraction identifies authentication-related failures and checkout symptoms.
3. Retrieval pulls code context from Ordering and Identity boundaries.
4. Causal analysis notices that the observed failure pattern is more consistent
   with upstream identity/session issues than with core ordering business logic.
5. Severity estimates customer-facing impact.
6. The ticket is created for the team that owns the likely Identity fault domain.

**Why the scenario matters**

This is the clearest demonstration that Upstream does not blindly trust the
reporter.
It reassigns ownership based on evidence,
not on the location where the symptom surfaced.

### Use Case 2 — Silent EventBus

**Scenario**

The reporter again blames Ordering,
but the real problem is that expected downstream events are not being published
or consumed.
The absence of EventBus activity is the strongest clue.

**How Upstream handles it**

1. Extraction identifies the expected business action from the report and logs.
2. Retrieval brings in EventBus and ordering integration context.
3. Causal analysis treats missing expected event flow as signal,
   not as lack of information.
4. The agent forms a hypothesis that the messaging layer
   or RabbitMQ path is the more plausible owner.
5. The Jira mock ticket records both the reporter's original assumption
   and the agent's evidence-backed disagreement.

**Why the scenario matters**

This scenario proves that operational silence can still be evidence.
It also demonstrates that service ownership can sit in infrastructure or message
transport,
not only in the service whose API endpoint was hit first.

### Use Case 3 — Prompt injection

**Scenario**

A malicious actor tries to smuggle instructions into the incident payload,
for example by telling the model to ignore previous rules,
reassign the ticket,
or expose system details.

**How Upstream handles it**

1. Guardrails inspect the text and attachments before the main graph proceeds.
2. Injection patterns or policy violations trigger a rejection or security flow.
3. The core analysis LLM path is not executed with the unsafe payload.
4. A safe outcome is recorded for observability and later review.

**Why the scenario matters**

This scenario demonstrates that Upstream is not merely an automation pipeline.
It is an agentic system with explicit safety boundaries.
The most impressive reasoning path is useless if the intake layer is easy to
manipulate.

### Shared value across all use cases

All three scenarios show the same product pattern:

- intake is messy
- evidence is incomplete
- the reporter may be wrong
- the system still needs to produce a grounded next action

That is the operational niche Upstream is built for.

## 6. Observability

> **⚠️ Evidence pending — to be completed in Phase 13.**
>
> This section requires runtime screenshots and log samples that will be captured
> after the agent is fully implemented and the demo scenarios are validated.
> Placeholders will be replaced with actual Langfuse trace exports, structured log
> samples with correlation IDs, and screenshots of guardrail rejections in action.

Planned observability signals include:

- Langfuse traces per graph execution
- per-node latency and token/cost visibility
- correlation IDs across UI, agent, Jira mock, and notification mock
- structured `structlog` events for each handoff and failure
- ticket and notification audit events for downstream actions

## 7. Security & Guardrails

> **⚠️ Evidence pending — to be completed in Phase 13.**
>
> This section requires runtime screenshots and log samples that will be captured
> after the agent is fully implemented and the demo scenarios are validated.
> Placeholders will be replaced with actual Langfuse trace exports, structured log
> samples with correlation IDs, and screenshots of guardrail rejections in action.

The current security design assumptions are:

- payload validation runs before the main analysis flow
- prompt injection attempts are blocked or rerouted early
- tool calls to downstream mocks are constrained and typed
- the agent only works with an indexed snapshot of allowed code context
- provider choice is explicit so privacy-sensitive deployments can use Ollama

## 8. Scalability

Upstream is currently scoped as a single-instance hackathon system,
but the architecture is intentionally chosen so it can scale along familiar
service boundaries.

### Current capacity target

The working planning target is approximately **10 concurrent incidents per agent
instance** for the initial deployment profile.
That is not a hard benchmark.
It is a practical design target that keeps the graph responsive while model
latency remains the dominant cost.

### Scaling approach

The intended path is horizontal:

- multiple stateless agent replicas behind a load balancer
- a queue-based intake layer for async smoothing
- Qdrant scaled independently from the API services
- Langfuse and storage moved to production-grade backing services

### Primary bottlenecks

The main expected bottlenecks are:

- LLM latency during extraction and causal analysis
- vector search performance under much higher QPS
- the single-writer nature of the SQLite checkpointer
- single-instance mock services with file-backed storage

For the detailed analysis and production-hardening roadmap,
see [SCALING.md](SCALING.md).

## 9. Lessons Learned

This section is intentionally reserved for the post-implementation retrospective.

**TODO for Phase 12 / QA**

- document what worked better than expected
- document where the graph became more complex than necessary
- record provider trade-offs observed in practice
- record retrieval and guardrail failure modes
- capture what we would change before turning the demo into a production system
