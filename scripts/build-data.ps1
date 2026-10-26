$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
docker info *> $null
if ($LASTEXITCODE -ne 0) { throw 'Docker Linux engine is unavailable.' }
docker compose run --rm --build prepare-data
if ($LASTEXITCODE -ne 0) { throw 'Dataset preparation failed.' }
docker compose run --rm --no-deps --build --use-aliases spark-job --master spark://spark-master:7077 --conf spark.driver.host=spark-job --conf spark.driver.bindAddress=0.0.0.0 --conf spark.executor.memory=512m /app/jobs/build_tables.py
if ($LASTEXITCODE -ne 0) { throw 'Table build failed. See logs; no passed manifest was published.' }
