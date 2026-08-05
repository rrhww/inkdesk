[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$F01EvidenceDir,
    [string]$ComposeFile = (Join-Path $PSScriptRoot "..\..\infra\docker-compose.local-docker.yml"),
    [string]$OutputDirectory
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
$serverRoot = Join-Path $repoRoot "server"
$f01Root = [IO.Path]::GetFullPath($F01EvidenceDir)

function Invoke-F02External {
    param([Parameter(Mandatory)][string]$Executable, [Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) { throw "F02 command failed: $Executable" }
}

function Assert-F02EvidenceRoot {
    param([Parameter(Mandatory)][string]$Path)
    if (-not (Test-Path -LiteralPath (Join-Path $Path "manifest.json") -PathType Leaf)) { throw "F02 requires an F01 manifest" }
    if ($Path -notmatch '[\\/]\.local[\\/]f01-baseline[\\/]') { throw "F02 only accepts F01 evidence below .local/f01-baseline" }
}

function Assert-F02DatabaseName {
    param([Parameter(Mandatory)][string]$Name)
    if ($Name.Length -gt 63 -or $Name -notmatch '^inkdesk_f02_(empty|adopt|invalid|permission)_[A-Za-z0-9_]+$') {
        throw "F02 database target is not an allowed isolated name"
    }
}

function Assert-F02RoleName {
    param([Parameter(Mandatory)][string]$Name)
    if ($Name.Length -gt 63 -or $Name -notmatch '^inkdesk_f02_migrator_[A-Za-z0-9_]+$') {
        throw "F02 migration role is not an allowed isolated name"
    }
}

function Invoke-F02Migration {
    param([Parameter(Mandatory)][string]$DatabaseUrl, [Parameter(Mandatory)][ValidateSet("status", "check", "upgrade")][string]$Command)
    $previousUrl = $env:INKDESK_DB_URL
    try {
        $env:INKDESK_DB_URL = $DatabaseUrl
        Push-Location $serverRoot
        & python -m inkdesk_server.db_migrations $Command
        if ($LASTEXITCODE -ne 0) { throw "F02 migration command failed: $Command" }
    } finally {
        Pop-Location
        $env:INKDESK_DB_URL = $previousUrl
    }
}

function Invoke-F02Fingerprint {
    param([Parameter(Mandatory)][string]$DatabaseUrl, [Parameter(Mandatory)][string]$Output)
    Invoke-F02External python (Join-Path $repoRoot "scripts\f01\fingerprint_database.py") --database-url $DatabaseUrl --output $Output --exclude-table alembic_version
}

function Invoke-F02SchemaCapture {
    param([Parameter(Mandatory)][string]$DatabaseUrl, [Parameter(Mandatory)][string]$Output)
    Invoke-F02External python (Join-Path $repoRoot "scripts\f01\export_postgres_schema.py") capture --database-url $DatabaseUrl --snapshot $Output --exclude-table alembic_version
}

Assert-F02EvidenceRoot -Path $f01Root
Invoke-F02External python (Join-Path $repoRoot "scripts\f01\verify_baseline.py") --manifest (Join-Path $f01Root "manifest.json") --evidence-root $f01Root --known-issues (Join-Path $repoRoot "docs\delivery\baselines\f01\known-issues.json")

$runId = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $repoRoot ".local\f02-migrations\$runId" }
$outputRoot = [IO.Path]::GetFullPath($OutputDirectory)
if ($outputRoot -notmatch '[\\/]\.local[\\/]f02-migrations[\\/]') { throw "F02 output must be below .local/f02-migrations" }
if (Test-Path -LiteralPath $outputRoot) { throw "F02 output directory already exists" }
New-Item -ItemType Directory -Path $outputRoot, (Join-Path $outputRoot "artifacts") | Out-Null

$composePath = [IO.Path]::GetFullPath($ComposeFile)
$config = (& docker compose -f $composePath config --format json | ConvertFrom-Json)
if ($LASTEXITCODE -ne 0) { throw "F02 could not read Docker Compose configuration" }
$postgres = $config.services.'local-postgres'
if ($null -eq $postgres) { throw "F02 verifier requires local-postgres" }
$containerId = (& docker compose -f $composePath ps -q local-postgres).Trim()
if (-not $containerId) { throw "F02 verifier requires a running local-postgres service" }
$port = ((& docker compose -f $composePath port local-postgres 5432).Trim() -split ':')[-1]
$user = [string]$postgres.environment.POSTGRES_USER
$password = [string]$postgres.environment.POSTGRES_PASSWORD
$escapedUser = [uri]::EscapeDataString($user)
$escapedPassword = [uri]::EscapeDataString($password)

$suffix = ($runId -replace '[^A-Za-z0-9_]', '_').ToLowerInvariant()
$emptyDatabase = "inkdesk_f02_empty_$suffix"
$adoptDatabase = "inkdesk_f02_adopt_$suffix"
$invalidDatabase = "inkdesk_f02_invalid_$suffix"
$permissionDatabase = "inkdesk_f02_permission_$suffix"
$permissionRole = "inkdesk_f02_migrator_$suffix"
$permissionPassword = [guid]::NewGuid().ToString("N")
foreach ($name in @($emptyDatabase, $adoptDatabase, $invalidDatabase, $permissionDatabase)) { Assert-F02DatabaseName -Name $name }
Assert-F02RoleName -Name $permissionRole
$emptyUrl = "postgresql+psycopg://$escapedUser`:$escapedPassword@127.0.0.1`:$port/$emptyDatabase"
$adoptUrl = "postgresql+psycopg://$escapedUser`:$escapedPassword@127.0.0.1`:$port/$adoptDatabase"
$invalidUrl = "postgresql+psycopg://$escapedUser`:$escapedPassword@127.0.0.1`:$port/$invalidDatabase"
$permissionUrl = "postgresql+psycopg://$permissionRole`:$permissionPassword@127.0.0.1`:$port/$permissionDatabase"
$checks = New-Object System.Collections.Generic.List[object]
$created = New-Object System.Collections.Generic.List[string]
$success = $false

try {
    Invoke-F02External docker compose -f $composePath exec -T local-postgres psql -U $user --dbname postgres --set ON_ERROR_STOP=1 -c "CREATE DATABASE $emptyDatabase"
    $created.Add($emptyDatabase)
    Invoke-F02Migration -DatabaseUrl $emptyUrl -Command upgrade
    $emptySchema = Join-Path $outputRoot "artifacts\fresh-schema.json"
    Invoke-F02SchemaCapture -DatabaseUrl $emptyUrl -Output $emptySchema
    if (((Get-Content -Raw $emptySchema | ConvertFrom-Json).compatibilityDigest) -ne "4c7413a2ef0b1c571513bbeb672c9f18dc8afd9cf0a64e1fa7533c4a9c6ba519") {
        throw "Fresh F02 schema does not match the F01 compatibility digest"
    }
    $checks.Add([ordered]@{ name = "fresh-upgrade"; status = "PASS"; artifacts = @($emptySchema) })

    Invoke-F02External docker compose -f $composePath exec -T local-postgres psql -U $user --dbname postgres --set ON_ERROR_STOP=1 -c "CREATE DATABASE $adoptDatabase"
    $created.Add($adoptDatabase)
    $dumpInContainer = "/tmp/f02-$adoptDatabase.dump"
    Invoke-F02External docker cp (Join-Path $f01Root "backup\postgres.dump") "$containerId`:$dumpInContainer"
    Invoke-F02External docker compose -f $composePath exec -T local-postgres pg_restore --exit-on-error -U $user --dbname $adoptDatabase $dumpInContainer
    Invoke-F02External docker exec $containerId rm -f $dumpInContainer
    $beforeSchema = Join-Path $outputRoot "artifacts\adopt-before-schema.json"
    $afterSchema = Join-Path $outputRoot "artifacts\adopt-after-schema.json"
    $beforeData = Join-Path $outputRoot "artifacts\adopt-before-data.json"
    $afterData = Join-Path $outputRoot "artifacts\adopt-after-data.json"
    Invoke-F02SchemaCapture -DatabaseUrl $adoptUrl -Output $beforeSchema
    Invoke-F02Fingerprint -DatabaseUrl $adoptUrl -Output $beforeData
    Invoke-F02Migration -DatabaseUrl $adoptUrl -Command upgrade
    Invoke-F02SchemaCapture -DatabaseUrl $adoptUrl -Output $afterSchema
    Invoke-F02Fingerprint -DatabaseUrl $adoptUrl -Output $afterData
    if ((Get-FileHash $beforeSchema -Algorithm SHA256).Hash -ne (Get-FileHash $afterSchema -Algorithm SHA256).Hash) { throw "F02 adoption changed application schema" }
    if ((Get-FileHash $beforeData -Algorithm SHA256).Hash -ne (Get-FileHash $afterData -Algorithm SHA256).Hash) { throw "F02 adoption changed application data" }
    Invoke-F02Migration -DatabaseUrl $adoptUrl -Command upgrade
    $adoptVault = Join-Path $outputRoot "adopt-vault"
    Invoke-F02External python (Join-Path $repoRoot "scripts\f01\vault_archive.py") extract --archive (Join-Path $f01Root "backup\vault.zip") --destination $adoptVault --evidence-root (Join-Path $repoRoot ".local") --active-vault (Join-Path $f01Root "staging\vault") --output (Join-Path $outputRoot "artifacts\adopt-vault.json")
    Invoke-F02External python (Join-Path $repoRoot "scripts\f01\verify_restored_read_paths.py") --database-url $adoptUrl --vault-root $adoptVault --output (Join-Path $outputRoot "artifacts\adopt-read-paths.json")
    $checks.Add([ordered]@{ name = "f01-adoption"; status = "PASS"; artifacts = @($beforeSchema, $afterSchema, $beforeData, $afterData, (Join-Path $outputRoot "artifacts\adopt-read-paths.json")) })

    Invoke-F02External docker compose -f $composePath exec -T local-postgres psql -U $user --dbname postgres --set ON_ERROR_STOP=1 -c "CREATE DATABASE $invalidDatabase"
    $created.Add($invalidDatabase)
    Invoke-F02External docker compose -f $composePath exec -T local-postgres psql -U $user --dbname $invalidDatabase --set ON_ERROR_STOP=1 -c "CREATE TABLE partial_schema (id integer primary key)"
    $previousUrl = $env:INKDESK_DB_URL
    try {
        $env:INKDESK_DB_URL = $invalidUrl
        Push-Location $serverRoot
        & python -m inkdesk_server.db_migrations upgrade
        if ($LASTEXITCODE -eq 0) { throw "Unsupported schema was unexpectedly accepted" }
    } finally {
        Pop-Location
        $env:INKDESK_DB_URL = $previousUrl
    }
    $checks.Add([ordered]@{ name = "unsupported-schema"; status = "PASS"; artifacts = @() })

    Invoke-F02External docker compose -f $composePath exec -T local-postgres psql -U $user --dbname postgres --set ON_ERROR_STOP=1 -c "CREATE DATABASE $permissionDatabase"
    $created.Add($permissionDatabase)
    Invoke-F02External docker compose -f $composePath exec -T local-postgres psql -U $user --dbname postgres --set ON_ERROR_STOP=1 -c "CREATE ROLE $permissionRole LOGIN PASSWORD '$permissionPassword'; GRANT CONNECT ON DATABASE $permissionDatabase TO $permissionRole"
    Invoke-F02External docker compose -f $composePath exec -T local-postgres psql -U $user --dbname $permissionDatabase --set ON_ERROR_STOP=1 -c "REVOKE ALL ON SCHEMA public FROM PUBLIC; GRANT USAGE ON SCHEMA public TO $user"
    $previousUrl = $env:INKDESK_DB_URL
    $permissionOutput = @()
    try {
        $env:INKDESK_DB_URL = $permissionUrl
        Push-Location $serverRoot
        $permissionOutput = & python -m inkdesk_server.db_migrations upgrade
        if ($LASTEXITCODE -eq 0) { throw "DDL-restricted migration unexpectedly succeeded" }
    } finally {
        Pop-Location
        $env:INKDESK_DB_URL = $previousUrl
    }
    $permissionArtifact = Join-Path $outputRoot "artifacts\permission-failure.json"
    $permissionOutput | Set-Content -LiteralPath $permissionArtifact -Encoding utf8NoBOM
    if ((Get-Content -Raw $permissionArtifact) -notmatch 'DB_MIGRATION_FAILED') { throw "DDL-restricted migration did not return DB_MIGRATION_FAILED" }
    Invoke-F02External docker compose -f $composePath exec -T local-postgres psql -U $user --dbname $permissionDatabase --set ON_ERROR_STOP=1 -c "DO `$`$ BEGIN IF to_regclass('public.alembic_version') IS NOT NULL THEN RAISE EXCEPTION 'DDL-restricted migration wrote alembic_version'; END IF; END `$`$"
    $checks.Add([ordered]@{ name = "permission-failure"; status = "PASS"; artifacts = @($permissionArtifact) })

    $previousTestUrl = $env:INKDESK_TEST_PGVECTOR_URL
    try {
        $env:INKDESK_TEST_PGVECTOR_URL = "postgresql+psycopg://$escapedUser`:$escapedPassword@127.0.0.1`:$port/postgres"
        Push-Location $serverRoot
        Invoke-F02External python -m pytest tests/migrations/test_migration_lock.py -q
    } finally {
        Pop-Location
        $env:INKDESK_TEST_PGVECTOR_URL = $previousTestUrl
    }
    $checks.Add([ordered]@{ name = "migration-lock"; status = "PASS"; artifacts = @() })
    $success = $true
} finally {
    $cleanupFailed = $false
    foreach ($name in $created) {
        try { Invoke-F02External docker compose -f $composePath exec -T local-postgres psql -U $user --dbname postgres --set ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS $name WITH (FORCE)" } catch { $cleanupFailed = $true }
    }
    try { Invoke-F02External docker compose -f $composePath exec -T local-postgres psql -U $user --dbname postgres --set ON_ERROR_STOP=1 -c "DROP ROLE IF EXISTS $permissionRole" } catch { $cleanupFailed = $true }
    $checksDocument = [ordered]@{ checks = $checks.ToArray() }
    $checksPath = Join-Path $outputRoot "checks.json"
    $checksDocument | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $checksPath -Encoding utf8NoBOM
    if ($cleanupFailed -or -not $success) { exit 1 }
    Invoke-F02External python (Join-Path $PSScriptRoot "build-migration-report.py") --run-id $runId --f01-manifest (Join-Path $f01Root "manifest.json") --checks $checksPath --output (Join-Path $outputRoot "manifest.json")
}
