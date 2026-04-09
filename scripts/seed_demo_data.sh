#!/usr/bin/env bash
set -euo pipefail

JIRA_URL="${JIRA_URL:-http://localhost:3100}"
NOTIF_URL="${NOTIF_URL:-http://localhost:3200}"

if command -v py >/dev/null 2>&1; then
  PYTHON_CMD=(py -3)
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD=(python3)
elif command -v python >/dev/null 2>&1; then
  PYTHON_CMD=(python)
else
  echo "Python is required to parse JSON responses." >&2
  exit 1
fi

latest_ticket_id() {
  curl -sS "$JIRA_URL/api/tickets" | "${PYTHON_CMD[@]}" -c "import sys, json; tickets = json.load(sys.stdin); print(tickets[-1]['id'] if tickets else '')"
}

echo "Seeding Jira mock with demo tickets..."

curl -sS -X POST "$JIRA_URL/api/tickets" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Historical: Catalog images failing to load",
    "reporter": "Carla Rodriguez",
    "reporter_email": "carla@example.com",
    "reported_symptom": "Product images broken on the home page",
    "agent_hypothesis": "CDN cache invalidation issue. Catalog images returned 404 due to stale routing rules.",
    "suspected_service": "Catalog.API",
    "blast_radius": ["WebApp"],
    "severity": "medium",
    "assigned_team": "platform-team",
    "evidence": [],
    "incident_id": "INC-HIST-001"
  }' >/dev/null

LAST_ID="$(latest_ticket_id)"
curl -sS -X PATCH "$JIRA_URL/api/tickets/$LAST_ID/status" \
  -H "Content-Type: application/json" \
  -d '{"status": "resolved", "resolution_note": "CDN rules corrected"}' >/dev/null

curl -sS -X POST "$JIRA_URL/api/tickets" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Historical: Slow checkout on mobile",
    "reporter": "David Kim",
    "reporter_email": "david@example.com",
    "reported_symptom": "Mobile users report 8s+ checkout flow",
    "agent_hypothesis": "Mobile BFF aggregator is making sequential calls instead of parallel",
    "suspected_service": "Mobile.Bff.Shopping",
    "blast_radius": ["Ordering.API"],
    "severity": "medium",
    "assigned_team": "mobile-team",
    "evidence": [],
    "incident_id": "INC-HIST-002"
  }' >/dev/null

LAST_ID="$(latest_ticket_id)"
curl -sS -X PATCH "$JIRA_URL/api/tickets/$LAST_ID/status" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}' >/dev/null

curl -sS -X POST "$JIRA_URL/api/tickets" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Historical: Webhook deliveries lagging",
    "reporter": "Emma Rossi",
    "reporter_email": "emma@example.com",
    "reported_symptom": "External webhook subscribers receiving events 2-3 minutes late",
    "agent_hypothesis": "Webhooks.API delivery worker pool is undersized for current load",
    "suspected_service": "Webhooks.API",
    "blast_radius": [],
    "severity": "low",
    "assigned_team": "platform-team",
    "evidence": [],
    "incident_id": "INC-HIST-003"
  }' >/dev/null

echo "Done. Seeded 3 historical tickets in Jira mock."
echo "Open $JIRA_URL to verify."
