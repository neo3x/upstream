# Upstream Architecture

## Overview

Upstream is a multimodal SRE intake and triage system built as a small monorepo.
The architecture is intentionally split into visible services so the demo shows
an operational workflow,
not only a model call.

The stack contains:

- a reporter-facing UI
- the main agent service
- a Jira mock
- a notification mock
- Qdrant for retrieval
- Langfuse for observability

## Service Boundaries

### `services/ui`

The UI collects the incident report,
accepts a log upload,
and optionally accepts a screenshot.
It is built with FastAPI,
Jinja2,
HTMX,
and Tailwind to keep the interface lightweight and server-rendered.

### `services/agent`

The agent service contains the LangGraph workflow,
provider adapters,
retrieval logic,
guardrails,
and downstream integration clients.
This is where the core product behavior lives:
the ability to challenge the reporter's diagnosis with evidence.

### `services/jira_mock`

The Jira mock receives structured ticket payloads from the agent and displays
assignment state for the demo.
It exists so the project can show ticket creation and resolution without
depending on an external SaaS integration.

### `services/notification_mock`

The notification mock receives messages destined for responder teams and the
original reporter.
It makes the "closed-loop" nature of the system visible during the demo.

### `Qdrant`

Qdrant stores embeddings for the curated eShop snapshot.
The agent queries it to retrieve code chunks that help explain which service or
dependency is the most plausible owner of the incident.

### `Langfuse`

Langfuse captures execution traces,
prompt timing,
and model costs for the agent workflow.
It is part of the architecture because explainability matters in a system that
is allowed to disagree with the reporter.

## High-Level Flow

1. The reporter submits text,
   logs,
   and an optional screenshot.
2. Guardrails validate the input and detect unsafe prompt content.
3. The extraction step turns the raw payload into structured symptoms.
4. Retrieval fetches the most relevant eShop code chunks from Qdrant.
5. Causal analysis forms an evidence-backed hypothesis.
6. Severity estimation assigns priority and blast radius.
7. The agent creates a ticket in the Jira mock.
8. The responsible team is notified through the notification mock.
9. When the ticket is resolved,
   a smaller resolution flow sends a summary back to the reporter.

## State Management

The main workflow is implemented as a LangGraph graph with a typed state object.
Each node returns a state delta and LangGraph merges the result automatically.
The initial persistence strategy uses a SQLite-backed checkpointer for simplicity
and replayability.
The planned scale-out upgrade path is a Postgres-backed checkpointer.

## Error Handling

Each node is expected to catch operational errors,
record them in structured state,
and allow the graph to route to a fallback error-handling node.
The system should fail in a way that is:

- visible to developers
- safe for users
- traceable in Langfuse and logs

## Ports

The demo exposes only the interfaces needed for reviewers:

- `3000` — reporter UI
- `3001` — Langfuse dashboard
- `3100` — Jira mock
- `3200` — notification mock

## Diagram Status

The final architecture image referenced in the README will be generated in
Phase 5 and saved as `docs/architecture-diagram.png`.
