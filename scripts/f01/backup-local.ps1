[CmdletBinding()]
param(
    [ValidateSet("docker", "host")]
    [string]$Mode = "docker",
    [string]$RunDirectory,
    [string]$ComposeFile = (Join-Path $PSScriptRoot "..\..\infra\docker-compose.local-docker.yml"),
    [string]$SourceDatabaseUrl,
    [string]$VaultPath,
    [string]$RestoreDatabaseUrl,
    [string]$RestoreVaultTarget,
    [string]$PgDumpCommand = "pg_dump",
    [switch]$KeepServicesStopped
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Write-F01Json {
    param([Parameter(Mandatory)]$Value, [Parameter(Mandatory)][string]$Path)
    $Value | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $Path -Encoding utf8NoBOM
}

function Assert-F01RunDirectory {
    param([Parameter(Mandatory)][string]$Path)
    $fullPath = [IO.Path]::GetFullPath($Path)
    if ($fullPath -notmatch '[\\/]\.local[\\/]f01-baseline[\\/]') {
        throw "F01 evidence must be stored below repository .local/f01-baseline: $fullPath"
    }
    return $fullPath
}

function Invoke-F01External {
    param([Parameter(Mandatory)][string]$Executable, [Parameter(ValueFromRemainingArguments = $true)][string[]]$ArgumentList)
    & $Executable @ArgumentList
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed ($LASTEXITCODE): $Executable $($ArgumentList -join ' ')"
    }
}

function Get-F01DockerContext {
    param([Parameter(Mandatory)][string]$ComposePath)
    $composePath = [IO.Path]::GetFullPath($ComposePath)
    if (-not (Test-Path -LiteralPath $composePath -PathType Leaf)) {
        throw "Compose file does not exist: $composePath"
    }
    $config = (& docker compose -f $composePath config --format json | ConvertFrom-Json)
    if ($LASTEXITCODE -ne 0) { throw "Could not read Docker Compose configuration" }
    $postgres = $config.services.'local-postgres'
    $server = $config.services.'local-server'
    if ($null -eq $postgres -or $null -eq $server) {
        throw "F01 Docker mode requires local-postgres and local-server in the compose file"
    }
    $postgresId = (& docker compose -f $composePath ps -q local-postgres).Trim()
    $serverId = (& docker compose -f $composePath ps -q local-server).Trim()
    if (-not $postgresId -or -not $serverId) {
        throw "F01 requires running local-postgres and local-server services"
    }
    $serverPort = (& docker compose -f $composePath port local-server 8080).Trim()
    $postgresPort = (& docker compose -f $composePath port local-postgres 5432).Trim()
    if (-not $serverPort -or -not $postgresPort) {
        throw "F01 could not discover local-server or local-postgres published ports"
    }
    $serverPortNumber = ($serverPort -split ':')[-1]
    $postgresPortNumber = ($postgresPort -split ':')[-1]
    $environment = $postgres.environment
    $databaseName = [string]$environment.POSTGRES_DB
    $databaseUser = [string]$environment.POSTGRES_USER
    $databasePassword = [string]$environment.POSTGRES_PASSWORD
    $vaultRoot = [string]$server.environment.INKDESK_VAULT_ROOT
    if (-not $databaseName -or -not $databaseUser -or -not $databasePassword -or -not $vaultRoot) {
        throw "F01 could not resolve database or Vault configuration from Compose"
    }
    $escapedUser = [uri]::EscapeDataString($databaseUser)
    $escapedPassword = [uri]::EscapeDataString($databasePassword)
    return [pscustomobject]@{
        ComposeFile = $composePath
        PostgresService = "local-postgres"
        ServerService = "local-server"
        WebService = "local-web"
        PostgresContainerId = $postgresId
        ServerContainerId = $serverId
        DatabaseName = $databaseName
        DatabaseUser = $databaseUser
        DatabaseUrl = "postgresql://$escapedUser`:$escapedPassword@127.0.0.1`:$postgresPortNumber/$databaseName"
        ServerUrl = "http://127.0.0.1:$serverPortNumber"
        VaultRoot = $vaultRoot
    }
}

function Get-F01RunningServices {
    param([Parameter(Mandatory)]$Context)
    $running = @()
    foreach ($service in @($Context.WebService, $Context.ServerService)) {
        $containerId = (& docker compose -f $Context.ComposeFile ps --status running -q $service).Trim()
        if ($LASTEXITCODE -ne 0) { throw "Could not inspect Docker service state: $service" }
        if ($containerId) { $running += $service }
    }
    return $running
}

function Assert-F01Health {
    param([Parameter(Mandatory)][string]$ServerUrl)
    try {
        $response = Invoke-WebRequest -Uri "$ServerUrl/health" -TimeoutSec 15 -UseBasicParsing
    } catch {
        throw "F01 health precheck failed: $($_.Exception.Message)"
    }
    if ($response.StatusCode -ne 200) { throw "F01 health precheck returned HTTP $($response.StatusCode)" }
}

if (-not $RunDirectory) {
    throw "-RunDirectory is required"
}
$runRoot = Assert-F01RunDirectory -Path $RunDirectory
$backupDirectory = Join-Path $runRoot "backup"
$fingerprintDirectory = Join-Path $runRoot "fingerprints"
$stagingDirectory = Join-Path $runRoot "staging"
New-Item -ItemType Directory -Force -Path $backupDirectory, $fingerprintDirectory, $stagingDirectory | Out-Null

$quietStartedAt = $null
$quietEndedAt = $null
$interruptionReason = $null
$restoredServices = @()
$originalRunningServices = @()
$context = $null
$success = $false

try {
    if ($Mode -eq "host") {
        if (-not $SourceDatabaseUrl -or -not $VaultPath -or -not $RestoreDatabaseUrl -or -not $RestoreVaultTarget) {
            throw "Host mode requires -SourceDatabaseUrl, -VaultPath, -RestoreDatabaseUrl, and -RestoreVaultTarget"
        }
        if (-not (Test-Path -LiteralPath $VaultPath -PathType Container)) { throw "Vault path does not exist: $VaultPath" }
        if (-not (Get-Command $PgDumpCommand -ErrorAction SilentlyContinue)) { throw "Host mode requires an available pg_dump command: $PgDumpCommand" }
        $quietStartedAt = (Get-Date).ToUniversalTime().ToString("o")
        Invoke-F01External $PgDumpCommand --dbname $SourceDatabaseUrl --format custom --no-owner --no-acl --file (Join-Path $backupDirectory "postgres.dump")
        Invoke-F01External python (Join-Path $PSScriptRoot "fingerprint_database.py") --database-url $SourceDatabaseUrl --output (Join-Path $fingerprintDirectory "source-database.json")
        Invoke-F01External python (Join-Path $PSScriptRoot "vault_archive.py") fingerprint --source $VaultPath --output (Join-Path $fingerprintDirectory "source-vault.json")
        Invoke-F01External python (Join-Path $PSScriptRoot "vault_archive.py") archive --source $VaultPath --archive (Join-Path $backupDirectory "vault.zip") --output (Join-Path $backupDirectory "vault.json")
        $success = $true
        return
    }

    $context = Get-F01DockerContext -ComposePath $ComposeFile
    Assert-F01Health -ServerUrl $context.ServerUrl
    $originalRunningServices = Get-F01RunningServices -Context $context
    $quietStartedAt = (Get-Date).ToUniversalTime().ToString("o")
    if ($originalRunningServices.Count -gt 0) {
        Invoke-F01External docker compose -f $context.ComposeFile stop @originalRunningServices
    }

    $dumpPathInContainer = "/tmp/f01-postgres.dump"
    Invoke-F01External docker compose -f $context.ComposeFile exec -T $context.PostgresService pg_dump -U $context.DatabaseUser -d $context.DatabaseName -Fc --no-owner --no-acl -f $dumpPathInContainer
    Invoke-F01External docker cp "$($context.PostgresContainerId):$dumpPathInContainer" (Join-Path $backupDirectory "postgres.dump")
    Invoke-F01External docker exec $context.PostgresContainerId rm -f $dumpPathInContainer

    Invoke-F01External python (Join-Path $PSScriptRoot "fingerprint_database.py") --database-url $context.DatabaseUrl --output (Join-Path $fingerprintDirectory "source-database.json")
    $vaultStaging = Join-Path $stagingDirectory "vault"
    if (Test-Path -LiteralPath $vaultStaging) { throw "Refusing to reuse existing Vault staging directory: $vaultStaging" }
    New-Item -ItemType Directory -Path $vaultStaging | Out-Null
    Invoke-F01External docker cp "$($context.ServerContainerId):$($context.VaultRoot)/." $vaultStaging
    Invoke-F01External python (Join-Path $PSScriptRoot "vault_archive.py") fingerprint --source $vaultStaging --output (Join-Path $fingerprintDirectory "source-vault.json")
    Invoke-F01External python (Join-Path $PSScriptRoot "vault_archive.py") archive --source $vaultStaging --archive (Join-Path $backupDirectory "vault.zip") --output (Join-Path $backupDirectory "vault.json")
    $success = $true
} catch {
    $interruptionReason = $_.Exception.Message
    throw
} finally {
    $quietEndedAt = (Get-Date).ToUniversalTime().ToString("o")
    if ($context -and $originalRunningServices.Count -gt 0 -and -not $KeepServicesStopped) {
        try {
            Invoke-F01External docker compose -f $context.ComposeFile start @originalRunningServices
            $restoredServices = $originalRunningServices
        } catch {
            $interruptionReason = "$interruptionReason Service recovery failed: $($_.Exception.Message)".Trim()
            $success = $false
        }
    }
    $report = [ordered]@{
        mode = $Mode
        status = if ($success) { "PASS" } else { "FAIL" }
        quietWindow = [ordered]@{
            startedAt = $quietStartedAt
            endedAt = $quietEndedAt
            originallyRunningServices = $originalRunningServices
            restoredServices = $restoredServices
            servicesLeftStopped = [bool]$KeepServicesStopped
            interruptionReason = $interruptionReason
        }
    }
    Write-F01Json -Value $report -Path (Join-Path $backupDirectory "report.json")
}
