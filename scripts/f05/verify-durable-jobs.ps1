param(
  [string]$OutputDir = (Join-Path $PSScriptRoot '..\..\.local\f05-jobs')
)

$ErrorActionPreference = 'Stop'
if (-not $env:INKDESK_TEST_PGVECTOR_URL) {
  throw 'Set INKDESK_TEST_PGVECTOR_URL to an isolated PostgreSQL/pgvector instance before running F05 verification.'
}

$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$resolvedOutput = [IO.Path]::GetFullPath($OutputDir, $root)
New-Item -ItemType Directory -Force -Path $resolvedOutput | Out-Null
Push-Location (Join-Path $root 'server')
try {
  python -m pytest tests/jobs tests/migrations tests/spaces tests/test_compile_pipeline.py -q --junitxml (Join-Path $resolvedOutput 'pytest.xml')
  if ($LASTEXITCODE -ne 0) { throw 'F05 durable job verification failed.' }
} finally {
  Pop-Location
}
python (Join-Path $PSScriptRoot 'build-job-report.py') --junit (Join-Path $resolvedOutput 'pytest.xml') --output (Join-Path $resolvedOutput 'manifest.json')
if ($LASTEXITCODE -ne 0) { throw 'F05 manifest reported failure.' }
