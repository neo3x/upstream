# Upstream Quick Guide

## Prerequisites

- Docker and Docker Compose
- At least one LLM provider configured in `.env`
- Extra disk space if you plan to use Ollama for local inference

## Setup

```bash
git clone https://github.com/neo3x/upstream.git
cd upstream
cp .env.example .env
```

Open `.env` and choose one provider:

```bash
LLM_PROVIDER=claude
```

Supported values:

- `claude`
- `openai`
- `ollama`
- `mock`

Matching credentials:

- `claude` → set `ANTHROPIC_API_KEY`
- `openai` → set `OPENAI_API_KEY`
- `ollama` → no cloud key required, but the first run may download a multi-GB model

## Run

```bash
docker compose up --build
```

To enable the bundled Ollama container too:

```bash
docker compose --profile ollama up --build
```

The first build can take a few minutes because images are built,
the embedding model is prepared for the indexer,
and Langfuse takes longer than the other services to initialize.

## Main URLs

- `http://localhost:3000` — reporter UI
- `http://localhost:3001` — Langfuse
- `http://localhost:3100` — Jira mock
- `http://localhost:3200` — Notification mock
- `http://localhost:8000/health` — agent health check

Default Langfuse login:

- email: `demo@upstream.local`
- password: `demopassword`

## Demo Flow

From the repo root:

```bash
scripts/reset_state.sh
scripts/seed_demo_data.sh
scripts/run_demo.sh
```

If Claude is not configured locally, switch the scripted demo to Ollama:

```bash
export DEMO_LLM_PROVIDER=ollama
scripts/run_demo.sh
```

On Windows, run the bash scripts from Git Bash.
If you prefer native PowerShell:

```powershell
.\scripts\reset_state.ps1
.\scripts\seed_demo_data.ps1
$env:DEMO_LLM_PROVIDER="claude"
.\scripts\run_demo.ps1
```

## What To Expect

- `reset_state.sh` clears Jira mock and Notification mock state
- `seed_demo_data.sh` creates 3 historical Jira tickets
- `run_demo.sh` runs the 3 core scenarios:
  - Identity cascade
  - Silent EventBus
  - Prompt injection rejection

After a full scripted run you should see:

- 6 Jira tickets total
- 3 notifications total
- Langfuse traces for the processed incidents

## Troubleshooting

- If `docker compose up --build` fails, check that ports `3000`, `3001`, `3100`, `3200`, and `8000` are free
- If Langfuse loads slowly, wait 30–60 seconds and refresh
- If Ollama is slow or fails on first use, check available disk and memory
- If the UI loads but submissions fail, verify the agent is reachable at `http://localhost:8000/health`
- For more detail, see [docs/troubleshooting.md](docs/troubleshooting.md)
