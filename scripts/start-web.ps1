$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
docker compose up -d opa
if ($LASTEXITCODE -ne 0) { throw 'OPA startup failed' }
docker compose -f compose.yaml -f compose.web.yaml --profile web up -d --build --no-deps web
if ($LASTEXITCODE -ne 0) { throw 'Web application startup failed' }
Write-Host 'Open http://localhost:8090 after Spark initialization. Stop web before batch evaluations to free worker memory.'
