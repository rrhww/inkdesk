$ErrorActionPreference = "SilentlyContinue"
for ($i = 1; $i -le 60; $i++) {
    Start-Sleep -Seconds 5
    docker ps 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Docker ready after $i attempts!"
        docker ps --format "table {{.Names}}\t{{.Status}}"
        exit 0
    }
    Write-Host "Waiting... ($i/60)"
}
Write-Host "Docker not ready after 60 attempts"
exit 1
