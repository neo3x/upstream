# Troubleshooting

This document collects common local setup issues for Upstream.
It will expand as implementation phases add more runnable behavior.

## Ports Already In Use

If `docker compose up --build` fails immediately,
check that these ports are free:

- `3000`
- `3001`
- `3100`
- `3200`

## Missing Provider Credentials

If the stack starts but LLM-backed actions fail,
check `.env` and confirm that the selected provider has its matching API key or
local runtime configured.

## Ollama Disk Usage

The first Ollama run may download several gigabytes of model data.
If that step fails,
check available disk space before retrying.

## Resetting Local State

As utility scripts are added in later phases,
the preferred reset path will move into `scripts/reset_state.sh`.
Until then,
you can reset the local environment by stopping the stack and removing the
relevant Docker volumes manually.
