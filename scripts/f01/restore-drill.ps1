[CmdletBinding()]
param(
    [ValidateSet("docker", "host")]
    [string]$Mode = "docker",
    [Parameter(Mandatory)][string]$RunDirectory,
    [string]$ComposeFile = (Join-Path $PSScriptRoot "..\..\infra\docker-compose.local-docker.yml"),
    [switch]$KeepRestoreTarget,
    [string]$RestoreDatabaseName,
    [string]$SourceDatabaseUrl,
    [string]$VaultPath,
    [string]$RestoreDatabaseUrl,
    [string]$RestoreVaultTarget,
    [string]$PgRestoreCommand = "pg_restore",
    [string]$PsqlCommand = "psql"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Write-F01RestoreJson {
    param([Parameter(Mandatory)]$Value, [Parameter(Mandatory)][string]$Path)
    $Value | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $Path -Encoding utf8NoBOM
}

function Assert-F01RestoreName {
    param([Parameter(Mandatory)][string]$Name, [Parameter(Mandatory)][string]$Source)
    if ($Name.Length -gt 63 -or $Name -eq $Source -or $Name -in @("postgres", "template0", "template1") -or $Name -notmatch '^inkdesk_f01_restore_[A-Za-z0-9_]+$') {
        throw "Restore database is not an allowed isolated target: $Name"
    }
}

function Get-F01GeneratedRestoreDatabaseName {
    param([Parameter(Mandatory)][string]$Suffix)
    $prefix = "inkdesk_f01_restore_"
    $maximumDatabaseNameLength = 63
    $candidate = "$prefix$Suffix"
    if ($candidate.Length -le $maximumDatabaseNameLength) { return $candidate }

    $digestBytes = [Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($Suffix))
    $digest = ([Convert]::ToHexString($digestBytes)).ToLowerInvariant().Substring(0, 12)
    $availableSuffixLength = $maximumDatabaseNameLength - $prefix.Length - $digest.Length - 1
    return "$prefix$($Suffix.Substring(0, $availableSuffixLength))_$digest"
}

function Invoke-F01RestoreExternal {
    param([Parameter(Mandatory)][string]$Executable, [Parameter(ValueFromRemainingArguments = $true)][string[]]$ArgumentList)
    & $Executable @ArgumentList
    if ($LASTEXITCODE -ne 0) { throw "Command failed ($LASTEXITCODE): $Executable $($ArgumentList -join ' ')" }
}

function Get-F01DatabaseNameFromUrl {
    param([Parameter(Mandatory)][string]$Url)
    try { $uri = [uri]$Url } catch { throw "Database URL is invalid" }
    $name = $uri.AbsolutePath.Trim('/')
    if (-not $name) { throw "Database URL must include a database name" }
    return $name
}

function Get-F01MaintenanceUrl {
    param([Parameter(Mandatory)][string]$Url)
    try { $uri = [uri]$Url } catch { throw "Database URL is invalid" }
    $builder = [System.UriBuilder]::new($uri)
    $builder.Path = "/postgres"
    return $builder.Uri.AbsoluteUri.TrimEnd('/')
}

function Get-F01RestoreDockerContext {
    param([Parameter(Mandatory)][string]$ComposePath)
    $composePath = [IO.Path]::GetFullPath($ComposePath)
    $config = (& docker compose -f $composePath config --format json | ConvertFrom-Json)
    if ($LASTEXITCODE -ne 0) { throw "Could not read Docker Compose configuration" }
    $postgres = $config.services.'local-postgres'
    $server = $config.services.'local-server'
    if ($null -eq $postgres -or $null -eq $server) { throw "F01 Docker mode requires local-postgres and local-server" }
    $postgresId = (& docker compose -f $composePath ps -aq local-postgres).Trim()
    $serverId = (& docker compose -f $composePath ps -aq local-server).Trim()
    $postgresPort = (& docker compose -f $composePath port local-postgres 5432).Trim()
    if (-not $postgresId -or -not $serverId -or -not $postgresPort) { throw "F01 requires running local-postgres and local-server" }
    $port = ($postgresPort -split ':')[-1]
    $database = [string]$postgres.environment.POSTGRES_DB
    $user = [string]$postgres.environment.POSTGRES_USER
    $password = [string]$postgres.environment.POSTGRES_PASSWORD
    $vault = [string]$server.environment.INKDESK_VAULT_ROOT
    if (-not $database -or -not $user -or -not $password -or -not $vault) { throw "Could not resolve Compose database or Vault configuration" }
    return [pscustomobject]@{
        ComposeFile = $composePath; PostgresService = "local-postgres"; PostgresContainerId = $postgresId; ServerContainerId = $serverId
        DatabaseName = $database; DatabaseUser = $user; DatabasePassword = $password; VaultRoot = $vault; Port = $port
    }
}

$runRoot = [IO.Path]::GetFullPath($RunDirectory)
if ($runRoot -notmatch '[\\/]\.local[\\/]f01-baseline[\\/]') { throw "F01 evidence must be below repository .local/f01-baseline" }
$backupDirectory = Join-Path $runRoot "backup"
$fingerprintDirectory = Join-Path $runRoot "fingerprints"
$restoreDirectory = Join-Path $runRoot "restore"
$dumpPath = Join-Path $backupDirectory "postgres.dump"
$vaultArchive = Join-Path $backupDirectory "vault.zip"
if (-not (Test-Path -LiteralPath $dumpPath -PathType Leaf) -or -not (Test-Path -LiteralPath $vaultArchive -PathType Leaf)) { throw "Backup artifacts are missing" }
New-Item -ItemType Directory -Force -Path $restoreDirectory | Out-Null

$context = $null
$targetDatabase = $null
$targetDatabaseCreated = $false
$targetVault = Join-Path $restoreDirectory "vault"
$cleanupStatus = "NOT_STARTED"
$reportStatus = "FAIL"
$interruptionReason = $null

try {
    if ($Mode -eq "host") {
        if (-not $SourceDatabaseUrl -or -not $VaultPath -or -not $RestoreDatabaseUrl -or -not $RestoreVaultTarget) {
            throw "Host mode requires -SourceDatabaseUrl, -VaultPath, -RestoreDatabaseUrl, and -RestoreVaultTarget"
        }
        if (-not (Test-Path -LiteralPath $VaultPath -PathType Container)) { throw "Host Vault path does not exist: $VaultPath" }
        if (-not (Get-Command $PgRestoreCommand -ErrorAction SilentlyContinue) -or -not (Get-Command $PsqlCommand -ErrorAction SilentlyContinue)) {
            throw "Host mode requires available pg_restore and psql commands"
        }
        $targetDatabase = Get-F01DatabaseNameFromUrl -Url $RestoreDatabaseUrl
        Assert-F01RestoreName -Name $targetDatabase -Source (Get-F01DatabaseNameFromUrl -Url $SourceDatabaseUrl)
        $targetVault = [IO.Path]::GetFullPath($RestoreVaultTarget)
        if ($targetVault -notlike "$runRoot*") { throw "Host restore Vault target must be inside this F01 run directory" }
        if ($targetVault -eq [IO.Path]::GetFullPath($VaultPath)) { throw "Host restore Vault target must not be the active Vault" }
        if ((Test-Path -LiteralPath $targetVault) -and (Get-ChildItem -LiteralPath $targetVault -Force | Select-Object -First 1)) { throw "Host restore Vault target is non-empty" }
        Invoke-F01RestoreExternal python (Join-Path $PSScriptRoot "fingerprint_database.py") --database-url $SourceDatabaseUrl --output (Join-Path $fingerprintDirectory "source-before-restore.json")
        Invoke-F01RestoreExternal python (Join-Path $PSScriptRoot "vault_archive.py") fingerprint --source $VaultPath --output (Join-Path $fingerprintDirectory "source-vault-before-restore.json")
        Invoke-F01RestoreExternal $PsqlCommand --dbname (Get-F01MaintenanceUrl -Url $RestoreDatabaseUrl) --set ON_ERROR_STOP=1 --command "CREATE DATABASE $targetDatabase"
        $targetDatabaseCreated = $true
        Invoke-F01RestoreExternal $PgRestoreCommand --exit-on-error --dbname $RestoreDatabaseUrl $dumpPath
        Invoke-F01RestoreExternal python (Join-Path $PSScriptRoot "fingerprint_database.py") --database-url $RestoreDatabaseUrl --output (Join-Path $fingerprintDirectory "restored-database.json")
        Invoke-F01RestoreExternal python (Join-Path $PSScriptRoot "vault_archive.py") extract --archive $vaultArchive --destination $targetVault --evidence-root $runRoot --active-vault $VaultPath --output (Join-Path $fingerprintDirectory "restored-vault.json")
        if ((Get-FileHash (Join-Path $fingerprintDirectory "source-database.json") -Algorithm SHA256).Hash -ne (Get-FileHash (Join-Path $fingerprintDirectory "restored-database.json") -Algorithm SHA256).Hash) { throw "Restored database fingerprint differs from source" }
        if ((Get-FileHash (Join-Path $fingerprintDirectory "source-vault.json") -Algorithm SHA256).Hash -ne (Get-FileHash (Join-Path $fingerprintDirectory "restored-vault.json") -Algorithm SHA256).Hash) { throw "Restored Vault fingerprint differs from source" }
        Invoke-F01RestoreExternal python (Join-Path $PSScriptRoot "verify_restored_read_paths.py") --database-url $RestoreDatabaseUrl --vault-root $targetVault --output (Join-Path $restoreDirectory "read-paths.json")
        Invoke-F01RestoreExternal python (Join-Path $PSScriptRoot "fingerprint_database.py") --database-url $SourceDatabaseUrl --output (Join-Path $fingerprintDirectory "source-after-restore.json")
        Invoke-F01RestoreExternal python (Join-Path $PSScriptRoot "vault_archive.py") fingerprint --source $VaultPath --output (Join-Path $fingerprintDirectory "source-vault-after-restore.json")
        if ((Get-FileHash (Join-Path $fingerprintDirectory "source-database.json") -Algorithm SHA256).Hash -ne (Get-FileHash (Join-Path $fingerprintDirectory "source-after-restore.json") -Algorithm SHA256).Hash) { throw "Source database changed during restore drill" }
        if ((Get-FileHash (Join-Path $fingerprintDirectory "source-vault.json") -Algorithm SHA256).Hash -ne (Get-FileHash (Join-Path $fingerprintDirectory "source-vault-after-restore.json") -Algorithm SHA256).Hash) { throw "Source Vault changed during restore drill" }
        $reportStatus = "PASS"
        return
    }
    $context = Get-F01RestoreDockerContext -ComposePath $ComposeFile
    $suffix = ([IO.Path]::GetFileName($runRoot) -replace '[^A-Za-z0-9_]', '_').ToLowerInvariant()
    $targetDatabase = if ($RestoreDatabaseName) { $RestoreDatabaseName } else { Get-F01GeneratedRestoreDatabaseName -Suffix $suffix }
    Assert-F01RestoreName -Name $targetDatabase -Source $context.DatabaseName
    if ((Test-Path -LiteralPath $targetVault) -and (Get-ChildItem -LiteralPath $targetVault -Force | Select-Object -First 1)) { throw "Restore Vault target is non-empty" }

    $escapedUser = [uri]::EscapeDataString($context.DatabaseUser)
    $escapedPassword = [uri]::EscapeDataString($context.DatabasePassword)
    $sourceUrl = "postgresql+psycopg://$escapedUser`:$escapedPassword@127.0.0.1`:$($context.Port)/$($context.DatabaseName)"
    $targetUrl = "postgresql+psycopg://$escapedUser`:$escapedPassword@127.0.0.1`:$($context.Port)/$targetDatabase"
    Invoke-F01RestoreExternal python (Join-Path $PSScriptRoot "fingerprint_database.py") --database-url $sourceUrl --output (Join-Path $fingerprintDirectory "source-before-restore.json")
    Invoke-F01RestoreExternal python (Join-Path $PSScriptRoot "vault_archive.py") fingerprint --source (Join-Path $runRoot "staging\vault") --output (Join-Path $fingerprintDirectory "source-vault-before-restore.json")

    Invoke-F01RestoreExternal docker compose -f $context.ComposeFile exec -T $context.PostgresService psql -U $context.DatabaseUser --dbname postgres --set ON_ERROR_STOP=1 -c "CREATE DATABASE $targetDatabase"
    $targetDatabaseCreated = $true
    $dumpInContainer = "/tmp/f01-restore-$targetDatabase.dump"
    Invoke-F01RestoreExternal docker cp $dumpPath "$($context.PostgresContainerId):$dumpInContainer"
    Invoke-F01RestoreExternal docker compose -f $context.ComposeFile exec -T $context.PostgresService pg_restore --exit-on-error -U $context.DatabaseUser --dbname $targetDatabase $dumpInContainer
    Invoke-F01RestoreExternal docker exec $context.PostgresContainerId rm -f $dumpInContainer
    Invoke-F01RestoreExternal python (Join-Path $PSScriptRoot "fingerprint_database.py") --database-url $targetUrl --output (Join-Path $fingerprintDirectory "restored-database.json")
    Invoke-F01RestoreExternal python (Join-Path $PSScriptRoot "vault_archive.py") extract --archive $vaultArchive --destination $targetVault --evidence-root $runRoot --active-vault (Join-Path $runRoot "staging\vault") --output (Join-Path $fingerprintDirectory "restored-vault.json")

    if ((Get-FileHash (Join-Path $fingerprintDirectory "source-database.json") -Algorithm SHA256).Hash -ne (Get-FileHash (Join-Path $fingerprintDirectory "restored-database.json") -Algorithm SHA256).Hash) { throw "Restored database fingerprint differs from source" }
    if ((Get-FileHash (Join-Path $fingerprintDirectory "source-vault.json") -Algorithm SHA256).Hash -ne (Get-FileHash (Join-Path $fingerprintDirectory "restored-vault.json") -Algorithm SHA256).Hash) { throw "Restored Vault fingerprint differs from source" }
    Invoke-F01RestoreExternal python (Join-Path $PSScriptRoot "verify_restored_read_paths.py") --database-url $targetUrl --vault-root $targetVault --output (Join-Path $restoreDirectory "read-paths.json")
    Invoke-F01RestoreExternal python (Join-Path $PSScriptRoot "fingerprint_database.py") --database-url $sourceUrl --output (Join-Path $fingerprintDirectory "source-after-restore.json")
    $sourceVaultAfter = Join-Path $runRoot "staging\vault-after-restore"
    if (Test-Path -LiteralPath $sourceVaultAfter) { throw "Refusing to reuse source Vault verification staging directory" }
    New-Item -ItemType Directory -Path $sourceVaultAfter | Out-Null
    Invoke-F01RestoreExternal docker cp "$($context.ServerContainerId):$($context.VaultRoot)/." $sourceVaultAfter
    Invoke-F01RestoreExternal python (Join-Path $PSScriptRoot "vault_archive.py") fingerprint --source $sourceVaultAfter --output (Join-Path $fingerprintDirectory "source-vault-after-restore.json")
    if ((Get-FileHash (Join-Path $fingerprintDirectory "source-database.json") -Algorithm SHA256).Hash -ne (Get-FileHash (Join-Path $fingerprintDirectory "source-after-restore.json") -Algorithm SHA256).Hash) { throw "Source database changed during restore drill" }
    if ((Get-FileHash (Join-Path $fingerprintDirectory "source-vault.json") -Algorithm SHA256).Hash -ne (Get-FileHash (Join-Path $fingerprintDirectory "source-vault-after-restore.json") -Algorithm SHA256).Hash) { throw "Source Vault changed during restore drill" }
    $reportStatus = "PASS"
} catch {
    $interruptionReason = $_.Exception.Message
    throw
} finally {
    try {
        if (-not $KeepRestoreTarget -and $targetDatabaseCreated -and $context) {
            Invoke-F01RestoreExternal docker compose -f $context.ComposeFile exec -T $context.PostgresService psql -U $context.DatabaseUser --dbname postgres --set ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS $targetDatabase WITH (FORCE)"
        }
        if (-not $KeepRestoreTarget -and $targetDatabaseCreated -and $Mode -eq "host" -and $RestoreDatabaseUrl) {
            Invoke-F01RestoreExternal $PsqlCommand --dbname (Get-F01MaintenanceUrl -Url $RestoreDatabaseUrl) --set ON_ERROR_STOP=1 --command "DROP DATABASE IF EXISTS $targetDatabase WITH (FORCE)"
        }
        if (-not $KeepRestoreTarget -and (Test-Path -LiteralPath $targetVault)) {
            Remove-Item -LiteralPath $targetVault -Recurse -Force
        }
        $cleanupStatus = if ($KeepRestoreTarget) { "KEPT_BY_OPERATOR" } else { "CLEANED" }
    } catch {
        $cleanupStatus = "FAILED"
        $reportStatus = "FAIL"
        $interruptionReason = "$interruptionReason Cleanup failed: $($_.Exception.Message)".Trim()
    }
    Write-F01RestoreJson -Value ([ordered]@{
        status = $reportStatus; targetDatabase = $targetDatabase; targetVault = "restore/vault"; cleanupStatus = $cleanupStatus
        keepRestoreTarget = [bool]$KeepRestoreTarget; interruptionReason = $interruptionReason
    }) -Path (Join-Path $restoreDirectory "report.json")
}
