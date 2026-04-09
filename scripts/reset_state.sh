#!/usr/bin/env bash
set -euo pipefail

JIRA_URL="${JIRA_URL:-http://localhost:3100}"
NOTIF_URL="${NOTIF_URL:-http://localhost:3200}"

echo "Resetting Upstream demo state..."

curl -sS -X POST "$JIRA_URL/api/reset" >/dev/null && echo "  ✓ Jira mock cleared"
curl -sS -X POST "$NOTIF_URL/api/reset" >/dev/null && echo "  ✓ Notifications cleared"

# Intentionally do not clear Langfuse traces. The observability history is
# useful across demo takes.
# If you need to reset agent checkpoints too:
# docker exec upstream-agent rm -f /app/data/checkpoints/upstream.sqlite && echo "  ✓ Agent checkpoints cleared"

echo "Done. Run scripts/seed_demo_data.sh to repopulate baseline tickets."
