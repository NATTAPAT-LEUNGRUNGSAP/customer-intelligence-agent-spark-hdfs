param(
    [Parameter(Mandatory=$true)][string]$Manifest,
    [ValidateSet('dev','regression','regression-v2','regression-v3','regression-v4','regression-v5','holdout')][string]$Split = 'dev',
    [string]$Model = 'qwen3.5:9b'
)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
docker compose run --rm --no-deps --use-aliases spark-job --master spark://spark-master:7077 --conf spark.driver.host=spark-job --conf spark.driver.bindAddress=0.0.0.0 --conf spark.executor.memory=512m /app/jobs/evaluate.py --manifest $Manifest --model $Model --split $Split
if ($LASTEXITCODE -ne 0) { throw 'Evaluation failed or incomplete; inspect report status.' }
