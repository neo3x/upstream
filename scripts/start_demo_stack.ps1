param(
    [string]$EnvFile = ".env",
    [switch]$WithOllama
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

if (-not (Test-Path $EnvFile)) {
    throw "Missing $EnvFile. Copy .env.example to .env and configure your provider first."
}

$provider = ""
$envLines = Get-Content $EnvFile -ErrorAction Stop
foreach ($line in $envLines) {
    if ($line -match '^\s*LLM_PROVIDER\s*=\s*(.+?)\s*$') {
        $provider = $Matches[1].Trim().Trim('"').Trim("'")
        break
    }
}

$composeArgs = @("compose")
if ($WithOllama -or $provider -eq "ollama") {
    $composeArgs += @("--profile", "ollama")
}
$composeArgs += @("up", "-d", "--build")

Write-Step "Starting full Upstream stack"
& docker @composeArgs

Write-Step "Waiting for agent health check"
$healthy = $false
for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 3
    try {
        $health = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get
        if ($health.service -eq "upstream-agent") {
            $healthy = $true
            break
        }
    } catch {
    }
}

if (-not $healthy) {
    throw "Agent did not become healthy on http://localhost:8000/health"
}

Write-Host ""
Write-Host "Upstream demo stack is ready." -ForegroundColor Green
Write-Host "UI:            http://localhost:3000"
Write-Host "Agent health:  http://localhost:8000/health"
Write-Host "Langfuse:      http://localhost:3001"
Write-Host "Jira mock:     http://localhost:3100"
Write-Host "Notifications: http://localhost:3200"
