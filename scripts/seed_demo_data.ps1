param(
    [string]$JiraUrl = "http://localhost:3100"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function New-Ticket($Payload) {
    Invoke-RestMethod -Uri "$JiraUrl/api/tickets" -Method Post -ContentType "application/json" -Body ($Payload | ConvertTo-Json -Depth 10) | Out-Null
}

function Get-LatestTicketId {
    $tickets = Invoke-RestMethod -Uri "$JiraUrl/api/tickets" -Method Get
    if ($tickets.Count -eq 0) {
        throw "No tickets returned from Jira mock."
    }
    return $tickets[-1].id
}

function Set-TicketStatus([string]$TicketId, [string]$Status, [string]$ResolutionNote = "") {
    $body = @{ status = $Status }
    if ($ResolutionNote) {
        $body.resolution_note = $ResolutionNote
    }
    Invoke-RestMethod -Uri "$JiraUrl/api/tickets/$TicketId/status" -Method Patch -ContentType "application/json" -Body ($body | ConvertTo-Json) | Out-Null
}

Write-Host "Seeding Jira mock with demo tickets..."

New-Ticket @{
    title = "Historical: Catalog images failing to load"
    reporter = "Carla Rodriguez"
    reporter_email = "carla@example.com"
    reported_symptom = "Product images broken on the home page"
    agent_hypothesis = "CDN cache invalidation issue. Catalog images returned 404 due to stale routing rules."
    suspected_service = "Catalog.API"
    blast_radius = @("WebApp")
    severity = "medium"
    assigned_team = "platform-team"
    evidence = @()
    incident_id = "INC-HIST-001"
}
Set-TicketStatus -TicketId (Get-LatestTicketId) -Status "resolved" -ResolutionNote "CDN rules corrected"

New-Ticket @{
    title = "Historical: Slow checkout on mobile"
    reporter = "David Kim"
    reporter_email = "david@example.com"
    reported_symptom = "Mobile users report 8s+ checkout flow"
    agent_hypothesis = "Mobile BFF aggregator is making sequential calls instead of parallel"
    suspected_service = "Mobile.Bff.Shopping"
    blast_radius = @("Ordering.API")
    severity = "medium"
    assigned_team = "mobile-team"
    evidence = @()
    incident_id = "INC-HIST-002"
}
Set-TicketStatus -TicketId (Get-LatestTicketId) -Status "in_progress"

New-Ticket @{
    title = "Historical: Webhook deliveries lagging"
    reporter = "Emma Rossi"
    reporter_email = "emma@example.com"
    reported_symptom = "External webhook subscribers receiving events 2-3 minutes late"
    agent_hypothesis = "Webhooks.API delivery worker pool is undersized for current load"
    suspected_service = "Webhooks.API"
    blast_radius = @()
    severity = "low"
    assigned_team = "platform-team"
    evidence = @()
    incident_id = "INC-HIST-003"
}

Write-Host "Done. Seeded 3 historical tickets in Jira mock."
Write-Host "Open $JiraUrl to verify."
