[CmdletBinding()]
param(
    [ValidateSet("contracts", "tests", "backup", "restore", "verify", "all")]
    [string]$Mode = "all",
    [string]$RunId = ((Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")),
    [string]$ComposeFile = (Join-Path $PSScriptRoot "..\..\infra\docker-compose.local-docker.yml"),
    [switch]$KeepRestoreTarget
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repositoryRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
$runDirectory = Join-Path $repositoryRoot ".local\f01-baseline\$RunId"
$contractsDirectory = Join-Path $repositoryRoot "docs\delivery\baselines\f01\contracts"
$knownIssuesPath = Join-Path $repositoryRoot "docs\delivery\baselines\f01\known-issues.json"
$manifestPath = Join-Path $runDirectory "manifest.json"
$testsDirectory = Join-Path $runDirectory "tests"
New-Item -ItemType Directory -Force -Path $runDirectory, $testsDirectory, (Join-Path $runDirectory "contracts") | Out-Null

function Invoke-F01Capture {
    param([Parameter(Mandatory)][scriptblock]$Action, [Parameter(Mandatory)][string]$Suite, [Parameter(Mandatory)][string]$Command)
    $started = Get-Date
    $stdoutPath = Join-Path $testsDirectory "$Suite.stdout.log"
    $stderrPath = Join-Path $testsDirectory "$Suite.stderr.log"
    try {
        & $Action 1> $stdoutPath 2> $stderrPath
        $exitCode = if ($LASTEXITCODE -eq $null) { 0 } else { $LASTEXITCODE }
    } catch {
        $_ | Out-String | Set-Content -LiteralPath $stderrPath -Encoding utf8NoBOM
        $exitCode = 1
    }
    $duration = ((Get-Date) - $started).TotalSeconds
    $recordPath = Join-Path $testsDirectory "$Suite.json"
    python (Join-Path $PSScriptRoot "classify_test_result.py") --suite $Suite --command $Command --exit-code $exitCode --duration $duration --stdout-file $stdoutPath --stderr-file $stderrPath --stdout-path "tests/$Suite.stdout.log" --stderr-path "tests/$Suite.stderr.log" --known-issues $knownIssuesPath --output $recordPath
    if ($LASTEXITCODE -ne 0) { throw "F01 could not classify captured command result: $Suite" }
    return Get-Content -Raw -LiteralPath $recordPath | ConvertFrom-Json
}

function Copy-F01Contract {
    param([Parameter(Mandatory)][string]$Name, [Parameter(Mandatory)][string]$SourcePath)
    $destination = Join-Path $runDirectory "contracts\$Name"
    Copy-Item -LiteralPath $SourcePath -Destination $destination -Force
    return [ordered]@{ name = [IO.Path]::GetFileNameWithoutExtension($Name); path = "contracts/$Name"; sha256 = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant(); status = "PASS" }
}

function Get-F01DockerInfo {
    param([Parameter(Mandatory)][string]$ComposePath)
    $config = (& docker compose -f $ComposePath config --format json | ConvertFrom-Json)
    if ($LASTEXITCODE -ne 0) { throw "Could not inspect Docker Compose configuration" }
    $postgresPortOutput = @(& docker compose -f $ComposePath port local-postgres 5432)
    $postgresPort = if ($postgresPortOutput.Count -eq 0) { "" } else { ([string]$postgresPortOutput[-1]).Trim() }
    $serverPortOutput = @(& docker compose -f $ComposePath port local-server 8080)
    $serverPort = if ($serverPortOutput.Count -eq 0) { "" } else { ([string]$serverPortOutput[-1]).Trim() }
    if (-not $postgresPort -or -not $serverPort) { throw "local-postgres and local-server must be running" }
    $postgres = $config.services.'local-postgres'
    $user = [string]$postgres.environment.POSTGRES_USER
    $password = [string]$postgres.environment.POSTGRES_PASSWORD
    $database = [string]$postgres.environment.POSTGRES_DB
    $port = ($postgresPort -split ':')[-1]
    return [pscustomobject]@{
        ServerUrl = "http://127.0.0.1:$((($serverPort -split ':')[-1]))"
        DatabaseUrl = "postgresql+psycopg://$([uri]::EscapeDataString($user))`:$([uri]::EscapeDataString($password))@127.0.0.1`:$port/$database"
        Database = $database
        DatabaseUser = $user
        ComposePostgresService = "local-postgres"
        ComposeFile = [IO.Path]::GetFullPath($ComposePath)
    }
}

function Invoke-F01PgvectorIntegration {
    param([Parameter(Mandatory)]$DockerInfo)
    $suffix = ($RunId -replace '[^A-Za-z0-9_]', '_').ToLowerInvariant()
    $database = "inkdesk_f01_pgvector_$suffix"
    if ($database -eq $DockerInfo.Database -or $database -notmatch '^inkdesk_f01_pgvector_[A-Za-z0-9_]+$') {
        throw "PGVector integration database is not an allowed isolated target: $database"
    }

    $databaseUrl = $DockerInfo.DatabaseUrl -replace "/$([regex]::Escape($DockerInfo.Database))$", "/$database"
    $created = $false
    $previousUrl = $env:INKDESK_TEST_PGVECTOR_URL

    try {
        & docker compose -f $DockerInfo.ComposeFile exec -T $DockerInfo.ComposePostgresService psql -U $DockerInfo.DatabaseUser -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE $database" | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Could not create isolated PGVector integration database: $database" }
        $created = $true
        $env:INKDESK_TEST_PGVECTOR_URL = $databaseUrl
        return Invoke-F01Capture -Suite "postgres-integration" -Command "cd server; INKDESK_TEST_PGVECTOR_URL=<isolated compose database>; python -m pytest tests/test_pgvector_integration.py" -Action {
            Push-Location (Join-Path $repositoryRoot "server")
            python -m pytest tests/test_pgvector_integration.py
            Pop-Location
        }
    } finally {
        if ($null -eq $previousUrl) {
            Remove-Item Env:INKDESK_TEST_PGVECTOR_URL -ErrorAction SilentlyContinue
        } else {
            $env:INKDESK_TEST_PGVECTOR_URL = $previousUrl
        }
        if ($created) {
            & docker compose -f $DockerInfo.ComposeFile exec -T $DockerInfo.ComposePostgresService psql -U $DockerInfo.DatabaseUser -d postgres -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS $database WITH (FORCE)" | Out-Null
            if ($LASTEXITCODE -ne 0) { throw "Could not clean isolated PGVector integration database: $database" }
        }
    }
}

function Write-F01Environment {
    param([Parameter(Mandatory)]$DockerInfo)
    $postgresVersion = (& docker compose -f $DockerInfo.ComposeFile exec -T local-postgres psql -U inkdesk -d $DockerInfo.Database -tAc "SHOW server_version" 2>$null).Trim()
    [ordered]@{
        os = [System.Environment]::OSVersion.VersionString
        python = (& python --version 2>&1).Trim()
        node = (& node --version 2>&1).Trim()
        npm = (& npm --version 2>&1).Trim()
        docker = (& docker version --format '{{.Server.Version}}' 2>&1).Trim()
        compose = (& docker compose version --short 2>&1).Trim()
        postgres = $postgresVersion
    } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runDirectory "environment.json") -Encoding utf8NoBOM
}

function Restore-F01Services {
    param([Parameter(Mandatory)][string]$ComposePath)
    $reportPath = Join-Path $runDirectory "backup\report.json"
    if (-not (Test-Path -LiteralPath $reportPath)) { return }
    $report = Get-Content -Raw -LiteralPath $reportPath | ConvertFrom-Json
    $services = @($report.quietWindow.originallyRunningServices)
    if ($services.Count -gt 0) {
        & docker compose -f $ComposePath start @services
        if ($LASTEXITCODE -ne 0) { throw "F01 failed to restore original service state: $($services -join ', ')" }
    }
}

function Get-F01SelectedKnownIssues {
    param([Parameter(Mandatory)][AllowEmptyCollection()][string[]]$IssueIds)
    $issueIdsPath = Join-Path $runDirectory "known-issue-ids.json"
    $outputPath = Join-Path $runDirectory "selected-known-issues.json"
    if ($IssueIds.Count -eq 0) {
        Set-Content -LiteralPath $issueIdsPath -Value "[]" -Encoding utf8NoBOM
    } else {
        @($IssueIds) | ConvertTo-Json | Set-Content -LiteralPath $issueIdsPath -Encoding utf8NoBOM
    }
    python (Join-Path $PSScriptRoot "capture_summary.py") select-known-issues --known-issues $knownIssuesPath --issue-ids $issueIdsPath --output $outputPath
    if ($LASTEXITCODE -ne 0) { throw "F01 could not select matched known issues" }
    return Get-Content -Raw -LiteralPath $outputPath | ConvertFrom-Json
}

function Get-F01CaptureSummary {
    param([Parameter(Mandatory)][string]$BackupStatus, [Parameter(Mandatory)][string]$RestoreStatus)
    $inputPath = Join-Path $runDirectory "capture-summary-input.json"
    $outputPath = Join-Path $runDirectory "capture-summary.json"
    [ordered]@{
        mode = $Mode
        contracts = @($contracts)
        tests = @($testRecords)
        backupStatus = $BackupStatus
        restoreStatus = $RestoreStatus
    } | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $inputPath -Encoding utf8NoBOM
    python (Join-Path $PSScriptRoot "capture_summary.py") summary --input $inputPath --output $outputPath
    if ($LASTEXITCODE -ne 0) { throw "F01 could not summarize capture status" }
    return Get-Content -Raw -LiteralPath $outputPath | ConvertFrom-Json
}

$startedAt = (Get-Date).ToUniversalTime().ToString("o")
$overallStatus = "FAIL"
$testRecords = @()
$contracts = @()
$backup = $null
$restore = $null
$sourceFingerprint = $null
$knownIssueIds = @()
$interruptionReason = $null
$dockerInfo = $null
$backupStatus = "FAIL"
$restoreStatus = "FAIL"

try {
    $dockerInfo = Get-F01DockerInfo -ComposePath $ComposeFile
    Write-F01Environment -DockerInfo $dockerInfo
    if ($Mode -in @("contracts", "all")) {
        $openapiResult = Invoke-F01Capture -Suite "openapi-compare" -Command "python scripts/f01/export_openapi.py compare" -Action {
            python (Join-Path $PSScriptRoot "export_openapi.py") compare --url $dockerInfo.ServerUrl --snapshot (Join-Path $contractsDirectory "openapi.json")
        }
        $schemaResult = Invoke-F01Capture -Suite "postgres-schema-compare" -Command "python scripts/f01/export_postgres_schema.py compare" -Action {
            python (Join-Path $PSScriptRoot "export_postgres_schema.py") compare --database-url $dockerInfo.DatabaseUrl --snapshot (Join-Path $contractsDirectory "postgres-schema.json") --exclude-table alembic_version
        }
        $testRecords += $openapiResult, $schemaResult
        if ($openapiResult.exitCode -ne 0 -or $schemaResult.exitCode -ne 0) { throw "F01 contract comparison failed" }
        $contracts += Copy-F01Contract -Name "openapi.json" -SourcePath (Join-Path $contractsDirectory "openapi.json")
        $contracts += Copy-F01Contract -Name "postgres-schema.json" -SourcePath (Join-Path $contractsDirectory "postgres-schema.json")
        $contracts += Copy-F01Contract -Name "representative-records.json" -SourcePath (Join-Path $contractsDirectory "representative-records.json")
        $contracts += Copy-F01Contract -Name "behavior-contracts.json" -SourcePath (Join-Path $contractsDirectory "behavior-contracts.json")
        $contracts += Copy-F01Contract -Name "browser-flows.json" -SourcePath (Join-Path $contractsDirectory "browser-flows.json")
    }
    if ($Mode -in @("tests", "all")) {
        $testRecords += Invoke-F01Capture -Suite "server" -Command "cd server; python -m pytest" -Action { Push-Location (Join-Path $repositoryRoot "server"); python -m pytest; Pop-Location }
        $testRecords += Invoke-F01Capture -Suite "web-test" -Command "cd web; npm test" -Action { Push-Location (Join-Path $repositoryRoot "web"); npm test; Pop-Location }
        $testRecords += Invoke-F01Capture -Suite "web-typecheck" -Command "cd web; npm run typecheck" -Action { Push-Location (Join-Path $repositoryRoot "web"); npm run typecheck; Pop-Location }
        $testRecords += Invoke-F01Capture -Suite "web-lint" -Command "cd web; npm run lint" -Action { Push-Location (Join-Path $repositoryRoot "web"); npm run lint; Pop-Location }
        $testRecords += Invoke-F01Capture -Suite "web-build" -Command "cd web; npm run build" -Action { Push-Location (Join-Path $repositoryRoot "web"); npm run build; Pop-Location }
        $testRecords += Invoke-F01Capture -Suite "web-e2e" -Command "cd web; INKDESK_API_BASE_URL=<compose server>; INKDESK_E2E_WEB_PORT=3304 npm run e2e" -Action { $env:INKDESK_API_BASE_URL = $dockerInfo.ServerUrl; $env:NEXT_PUBLIC_API_BASE_URL = $dockerInfo.ServerUrl; $env:INKDESK_E2E_WEB_PORT = "3304"; Push-Location (Join-Path $repositoryRoot "web"); npm run e2e; Pop-Location }
        $testRecords += Invoke-F01Capture -Suite "web-fullstack" -Command "cd web; INKDESK_API_BASE_URL=<compose server>; npm run e2e:fullstack" -Action {
            $env:INKDESK_API_BASE_URL = $dockerInfo.ServerUrl
            $env:NEXT_PUBLIC_API_BASE_URL = $dockerInfo.ServerUrl
            $env:INKDESK_E2E_WEB_PORT = "3304"
            Push-Location (Join-Path $repositoryRoot "web"); npm run e2e:fullstack; Pop-Location
        }
        $testRecords += Invoke-F01PgvectorIntegration -DockerInfo $dockerInfo
        if (@($testRecords | Where-Object { $_.status -notin @("PASS", "PASS_WITH_KNOWN_ISSUES") }).Count -gt 0) { throw "F01 test capture recorded failing or unavailable suites" }
    }
    if ($Mode -in @("backup", "all")) {
        & (Join-Path $PSScriptRoot "backup-local.ps1") -Mode docker -RunDirectory $runDirectory -ComposeFile $ComposeFile -KeepServicesStopped:($Mode -eq "all")
        if ($LASTEXITCODE -ne 0) { throw "F01 backup failed" }
        $backupReport = Get-Content -Raw -LiteralPath (Join-Path $runDirectory "backup\report.json") | ConvertFrom-Json
        if ($backupReport.status -ne "PASS") { throw "F01 backup report did not pass" }
        $vaultBackup = Get-Content -Raw -LiteralPath (Join-Path $runDirectory "backup\vault.json") | ConvertFrom-Json
        $backup = [ordered]@{
            status = $backupReport.status
            reportPath = "backup/report.json"
            database = [ordered]@{ path = "backup/postgres.dump"; format = "custom"; sha256 = (Get-FileHash -LiteralPath (Join-Path $runDirectory "backup\postgres.dump") -Algorithm SHA256).Hash.ToLowerInvariant() }
            vault = [ordered]@{ path = "backup/vault.zip"; fileCount = $vaultBackup.fileCount; sha256 = $vaultBackup.sha256 }
        }
        python (Join-Path $PSScriptRoot "capture_summary.py") source-fingerprint --database (Join-Path $runDirectory "fingerprints\source-database.json") --vault (Join-Path $runDirectory "fingerprints\source-vault.json") --output (Join-Path $runDirectory "fingerprints\source.json")
        if ($LASTEXITCODE -ne 0) { throw "F01 could not combine paired source fingerprints" }
        $sourceFingerprint = [ordered]@{ path = "fingerprints/source.json"; sha256 = (Get-FileHash -LiteralPath (Join-Path $runDirectory "fingerprints\source.json") -Algorithm SHA256).Hash.ToLowerInvariant() }
        $backupStatus = [string]$backupReport.status
    }
    if ($Mode -in @("restore", "all")) {
        & (Join-Path $PSScriptRoot "restore-drill.ps1") -Mode docker -RunDirectory $runDirectory -ComposeFile $ComposeFile -KeepRestoreTarget:$KeepRestoreTarget
        if ($LASTEXITCODE -ne 0) { throw "F01 restore drill failed" }
        $restoreReport = Get-Content -Raw -LiteralPath (Join-Path $runDirectory "restore\report.json") | ConvertFrom-Json
        if ($restoreReport.status -ne "PASS") { throw "F01 restore report did not pass" }
        $restore = [ordered]@{
            targetDatabase = [string]$restoreReport.targetDatabase
            targetVault = [string]$restoreReport.targetVault
            status = [string]$restoreReport.status
            cleanupStatus = [string]$restoreReport.cleanupStatus
            reportPath = "restore/report.json"
        }
        $restoreStatus = [string]$restoreReport.status
    }
    if ($Mode -in @("verify", "all")) {
        # Full verification runs after the final manifest has been written in finally.
    }
    if (@($testRecords | Where-Object { $_.status -in @("FAIL", "ENVIRONMENT_ERROR") }).Count -gt 0) { throw "F01 has failing or unavailable required test evidence" }
} catch {
    $interruptionReason = $_.Exception.Message
    throw
} finally {
    if ($Mode -eq "all" -and $dockerInfo) {
        try { Restore-F01Services -ComposePath $dockerInfo.ComposeFile } catch { $overallStatus = "FAIL"; $interruptionReason = "$interruptionReason Service recovery failed: $($_.Exception.Message)".Trim() }
    }
    $knownIssueIds = @($testRecords | ForEach-Object { @($_.knownIssueIds) } | Where-Object { $_ } | Sort-Object -Unique)
    if ($Mode -eq "all" -and -not $interruptionReason) {
        try {
            $summary = Get-F01CaptureSummary -BackupStatus $backupStatus -RestoreStatus $restoreStatus
            $overallStatus = [string]$summary.overallStatus
            $knownIssueIds = @($summary.knownIssueIds)
            if ($summary.reason) { $interruptionReason = [string]$summary.reason }
        } catch {
            $overallStatus = "FAIL"
            $interruptionReason = "$interruptionReason Capture summary failed: $($_.Exception.Message)".Trim()
        }
    }
    $completedAt = (Get-Date).ToUniversalTime().ToString("o")
    $gitCommit = (& git rev-parse HEAD 2>$null).Trim()
    $gitBranch = (& git branch --show-current 2>$null).Trim()
    $gitDirty = [bool]((& git status --porcelain).Trim())
    $environment = if (Test-Path (Join-Path $runDirectory "environment.json")) {
        Get-Content -Raw (Join-Path $runDirectory "environment.json") | ConvertFrom-Json
    } else {
        [ordered]@{ os = "unavailable"; python = "unavailable"; node = "unavailable"; npm = "unavailable"; docker = "unavailable"; compose = "unavailable"; postgres = "unavailable" }
    }
    if (-not $backup) { $backup = [ordered]@{ status = "FAIL"; reportPath = "backup/report.json"; database = [ordered]@{ path = "backup/unavailable.dump"; format = "unavailable"; sha256 = ("0" * 64) }; vault = [ordered]@{ path = "backup/unavailable.zip"; fileCount = 0; sha256 = ("0" * 64) } } }
    if (-not $sourceFingerprint) { $sourceFingerprint = [ordered]@{ path = "fingerprints/unavailable.json"; sha256 = ("0" * 64) } }
    if (-not $restore) { $restore = [ordered]@{ targetDatabase = "inkdesk_f01_restore_unavailable"; targetVault = "restore/vault"; status = "FAIL"; cleanupStatus = "NOT_STARTED"; reportPath = "restore/report.json" } }
    $manifest = [ordered]@{
        schemaVersion = "1.0"; runId = $RunId; startedAt = $startedAt; completedAt = $completedAt; overallStatus = $overallStatus
        git = [ordered]@{ commit = $gitCommit; branch = $gitBranch; dirty = $gitDirty }
        environment = $environment
        configuration = [ordered]@{ mode = "docker"; composeFile = $ComposeFile; services = @("local-postgres", "local-server", "local-web"); database = if ($dockerInfo) { $dockerInfo.Database } else { "" }; vaultSource = "compose-runtime" }
        contracts = $contracts; tests = $testRecords; backup = $backup; sourceFingerprint = $sourceFingerprint; restore = $restore; knownIssueIds = $knownIssueIds; knownIssues = @(Get-F01SelectedKnownIssues -IssueIds $knownIssueIds); interruptionReason = $interruptionReason
    }
    $manifest | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $manifestPath -Encoding utf8NoBOM
    if ($Mode -eq "all" -and $overallStatus -in @("PASS", "PASS_WITH_KNOWN_ISSUES")) {
        python (Join-Path $PSScriptRoot "verify_baseline.py") --manifest $manifestPath --evidence-root $runDirectory --known-issues $knownIssuesPath
        if ($LASTEXITCODE -ne 0) {
            $overallStatus = "FAIL"
            $interruptionReason = "$interruptionReason Evidence verification failed.".Trim()
            $manifest.overallStatus = $overallStatus
            $manifest.interruptionReason = $interruptionReason
            $manifest | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $manifestPath -Encoding utf8NoBOM
            throw "F01 evidence verification failed"
        }
    }
}
