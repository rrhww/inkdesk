$ErrorActionPreference = "Stop"
$base = "http://localhost:8080"

# 1. Create run
$createBody = @{
    type = "PRD"
    title = "SDK dogfooding: greeter module"
    goal = "Create a file server/inkdesk_server/cli_greeter.py with a function greet(name: str) -> str that returns 'Hello, {name}!', plus a if __name__ == '__main__' block that prints greet('World')."
} | ConvertTo-Json -Depth 3

Write-Host "=== 1. Creating run ===" -ForegroundColor Cyan
$run = Invoke-RestMethod -Uri "$base/api/runs" -Method Post -ContentType "application/json" -Body $createBody
$runId = $run.id
Write-Host "Run ID: $runId, Stage: $($run.currentStage)"

# 2. Context pack
Write-Host ""
Write-Host "=== 2. Context Pack ===" -ForegroundColor Cyan
$resp = Invoke-RestMethod -Uri "$base/api/runs/$runId/context-pack" -Method Post -ContentType "application/json"
Write-Host "Stage: $($resp.currentStage), Events: $($resp.events.Count)"

# Advance: context -> solution
$resp = Invoke-RestMethod -Uri "$base/api/runs/$runId/advance" -Method Post -ContentType "application/json" -Body '{"action":"approve"}'
Write-Host "Advanced to: $($resp.currentStage)"

# 3. Solution
Write-Host ""
Write-Host "=== 3. Solution ===" -ForegroundColor Cyan
$resp = Invoke-RestMethod -Uri "$base/api/runs/$runId/solution" -Method Post -ContentType "application/json"
Write-Host "Stage: $($resp.currentStage), Events: $($resp.events.Count)"

# Advance: solution -> review
$resp = Invoke-RestMethod -Uri "$base/api/runs/$runId/advance" -Method Post -ContentType "application/json" -Body '{"action":"approve"}'
Write-Host "Advanced to: $($resp.currentStage)"

# 4. Review
Write-Host ""
Write-Host "=== 4. Review ===" -ForegroundColor Cyan
$resp = Invoke-RestMethod -Uri "$base/api/runs/$runId/review" -Method Post -ContentType "application/json"
Write-Host "Stage: $($resp.currentStage), Events: $($resp.events.Count)"

# Advance: review -> coding
$resp = Invoke-RestMethod -Uri "$base/api/runs/$runId/advance" -Method Post -ContentType "application/json" -Body '{"action":"approve"}'
Write-Host "Advanced to: $($resp.currentStage)"

# 5. Coding execute (SDK)
Write-Host ""
Write-Host "=== 5. Coding Execute (SDK) ===" -ForegroundColor Yellow
$resp = Invoke-RestMethod -Uri "$base/api/runs/$runId/coding/execute" -Method Post -ContentType "application/json" -TimeoutSec 300
Write-Host "Stage: $($resp.currentStage), Events: $($resp.events.Count)"

# Print last 3 events
$lastEvents = $resp.events | Select-Object -Last 3
foreach ($ev in $lastEvents) {
    Write-Host ""
    Write-Host "--- Event: $($ev.eventType) ---" -ForegroundColor Green
    Write-Host ($ev.payload | ConvertTo-Json -Depth 5)
}

# 6. Check worktree
Write-Host ""
Write-Host "=== 6. Check Worktree ===" -ForegroundColor Cyan
$greeterPath = "e:\dev\projects\inkdesk-dogfood\server\inkdesk_server\cli_greeter.py"
if (Test-Path $greeterPath) {
    Write-Host "SUCCESS: cli_greeter.py created!" -ForegroundColor Green
    Get-Content $greeterPath
} else {
    Write-Host "WARNING: cli_greeter.py not found" -ForegroundColor Yellow
    Write-Host "Git status of worktree:"
    Push-Location "e:\dev\projects\inkdesk-dogfood"
    git status --short
    Pop-Location
}

Write-Host ""
Write-Host "=== Dogfooding Complete ===" -ForegroundColor Cyan
