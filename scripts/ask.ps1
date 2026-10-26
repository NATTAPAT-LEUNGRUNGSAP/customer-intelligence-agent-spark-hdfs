param(
    [Parameter(Mandatory=$true)][string]$Question,
    [Parameter(Mandatory=$true)][string]$Manifest,
    [string]$Model = 'qwen3.5:9b'
)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$jobArgs = @('--master','spark://spark-master:7077','--conf','spark.driver.host=spark-job',
    '--conf','spark.driver.bindAddress=0.0.0.0','--conf','spark.executor.memory=512m',
    '/app/jobs/agent.py',$Question,'--manifest',$Manifest,'--model',$Model)
docker compose run --rm --no-deps --use-aliases spark-job @jobArgs
if ($LASTEXITCODE -ne 0) { throw 'Agent execution failed. Inspect logs and reports.' }
