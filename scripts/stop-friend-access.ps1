$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
docker compose -f compose.yaml -f compose.web.yaml -f compose.share.yaml --profile web --profile share stop friend-tunnel friend-gateway
if ($LASTEXITCODE -ne 0) { throw 'Could not stop friend access; inspect Docker status.' }
Write-Host 'External friend access stopped. The local app remains available.'
