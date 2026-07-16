param([Parameter(Mandatory = $true)][string]$F01EvidenceDir)
$ErrorActionPreference = 'Stop'
$manifest = Join-Path $F01EvidenceDir 'manifest.json'
if (-not (Test-Path $manifest)) { throw "F01 manifest not found: $manifest" }
$data = Get-Content $manifest -Raw | ConvertFrom-Json
if ($data.overallStatus -ne 'PASS') { throw 'F04 verifier requires a PASS F01 manifest.' }
Push-Location (Join-Path $PSScriptRoot '..\..\server')
try {
  python -m pytest tests/spaces tests/migrations/test_f01_adoption.py -q
  if ($LASTEXITCODE -ne 0) { throw 'F04 focused verification failed.' }
} finally { Pop-Location }
