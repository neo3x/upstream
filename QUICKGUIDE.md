# QUICKGUIDE.md

# Upstream Quick Guide

## Prerequisites

- Docker and Docker Compose installed
- At least one LLM provider configured:
  Claude is recommended,
  OpenAI is supported,
  and Ollama is available for local/private deployments
- If using Ollama,
  make sure you have enough disk space for the first model download

## Setup (5 minutes)

```bash
git clone https://github.com/neo3x/upstream.git
cd upstream
cp .env.example .env
```

## Configure Your LLM Provider

Open `.env` and set:

```bash
LLM_PROVIDER=claude
```

Supported values:

- `claude`
- `openai`
- `ollama`

Then configure the matching credentials:

- If `LLM_PROVIDER=claude`, set `ANTHROPIC_API_KEY=...`
- If `LLM_PROVIDER=openai`, set `OPENAI_API_KEY=...`
- If `LLM_PROVIDER=ollama`, no cloud API key is required,
  but the first run may download a model of roughly 5 GB

## Run

```bash
docker compose up --build
```

Wait for all services to become healthy.
For a clean machine,
the first build may take 3-5 minutes because images are built and the eShop
snapshot is indexed for retrieval.

## Use

Open these URLs after the stack starts:

- `http://localhost:3000` — main reporter UI
- `http://localhost:3100` — Jira mock board
- `http://localhost:3200` — notification inbox
- `http://localhost:3001` — Langfuse traces dashboard

## Try The Demo Scenarios

- Pre-loaded log fixtures will live in `services/agent/tests/fixtures/`
- Submit one through the reporter UI to trigger triage
- Mark the created ticket as resolved in the Jira mock
- Check the notification mock to see the reporter-facing resolution update

## Reset State

The intended reset helper command is:

```bash
./scripts/reset_state.sh
```

If that helper has not been added yet in the current phase,
reset by stopping the stack and removing the relevant Docker volumes manually.

## Troubleshoot

- If `docker compose up` fails,
  check that ports `3000`,
  `3001`,
  `3100`,
  and `3200` are free
- If Ollama fails during the first model pull,
  check available disk space
- Expect roughly 10 GB of free disk if you plan to experiment with local models
- For expanded troubleshooting notes,
  see `docs/troubleshooting.md` once that document is added
