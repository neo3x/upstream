# Demo Scenarios

This document expands the three demo scenarios referenced in the README and
`AGENTS_USE.md`.

## 1. Identity Cascade

### Setup

The reporter sees checkout failures and assumes Ordering is the broken service.
The visible symptom appears downstream from the real cause.

### Expected Upstream Behavior

- Extract symptoms from the report and logs
- Retrieve relevant Ordering and Identity code context
- Identify the likely upstream identity failure
- Create a ticket for the team that actually owns the problem

### What This Proves

Upstream can disagree with the reporter and justify a reassignment with evidence.

## 2. Silent EventBus

### Setup

The reporter again blames Ordering,
but the strongest signal is the absence of expected event activity in the
message-bus path.

### Expected Upstream Behavior

- Recognize that "nothing happened" can still be evidence
- Retrieve EventBus-related code context
- Infer that RabbitMQ or the EventBus layer is the more plausible owner
- Route the ticket away from application logic when transport is the problem

### What This Proves

Upstream can use negative evidence,
not only explicit error strings.

## 3. Prompt Injection

### Setup

The reporter payload contains instructions intended to manipulate the model,
override system guidance,
or force a particular assignment result.

### Expected Upstream Behavior

- Detect the unsafe pattern during guardrails
- Prevent the main reasoning graph from running on the malicious payload
- Record the event for later review
- Return a safe rejection or security-oriented handling path

### What This Proves

Upstream treats safety as part of triage,
not as an afterthought.

## Reviewer Takeaway

The three demos are chosen to show three different capabilities:

- evidence-based disagreement
- infrastructure-aware causal analysis
- prompt injection defense
