$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
docker info *> $null
if ($LASTEXITCODE -ne 0) { throw 'Open Docker Desktop and wait until the Linux engine is running, then retry.' }
docker compose up -d --build --scale spark-worker=2
if ($LASTEXITCODE -ne 0) { throw 'Cluster startup failed. Inspect docker compose logs.' }
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    # Windows PowerShell 5 treats redirected native stderr as ErrorRecords.
    # Hadoop warnings must not abort readiness checks before exit-code handling.
    $previousErrorPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $report = docker compose exec -T namenode hdfs dfsadmin -report 2>$null
    $reportExit = $LASTEXITCODE
    $safeMode = docker compose exec -T namenode hdfs dfsadmin -safemode get 2>$null
    $safeModeExit = $LASTEXITCODE
    $ErrorActionPreference = $previousErrorPreference
    if (($reportExit -eq 0) -and ($safeModeExit -eq 0) -and (($report -join "`n") -match 'Live datanodes \(2\)') -and (($safeMode -join "`n") -match 'Safe mode is OFF')) {
        docker compose run --rm --no-deps --use-aliases spark-job
        if ($LASTEXITCODE -ne 0) { throw 'Spark/HDFS smoke test failed.' }
        exit 0
    }
    Start-Sleep -Seconds 2
}
throw 'Two DataNodes did not become available. Inspect docker compose logs.'
