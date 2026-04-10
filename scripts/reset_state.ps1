param(
    [string]$JiraUrl = "http://localhost:3100",
    [string]$NotificationUrl = "http://localhost:3200"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "Resetting Upstream demo state..."

Invoke-RestMethod -Uri "$JiraUrl/api/reset" -Method Post | Out-Null
Write-Host "  ✓ Jira mock cleared"

Invoke-RestMethod -Uri "$NotificationUrl/api/reset" -Method Post | Out-Null
Write-Host "  ✓ Notifications cleared"

Write-Host "Done. Run scripts/seed_demo_data.ps1 to repopulate baseline tickets."
