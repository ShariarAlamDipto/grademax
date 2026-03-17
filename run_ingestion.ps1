# GradeMax Phase 2 - Run Ingestion
# Sets environment variables and runs the ingestion pipeline
# DO NOT hardcode credentials here - use .env.local instead

if (-not (Test-Path ".env.local")) {
    Write-Error ".env.local not found. Copy .env.example to .env.local and fill in your credentials."
    exit 1
}
Get-Content ".env.local" | ForEach-Object {
    if ($_ -match "^([^#][^=]*)=(.*)$") {
        [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim())
    }
}

Write-Host "Starting ingestion pipeline..." -ForegroundColor Green
Write-Host ""

# Run ingestion
python scripts/ingest_pipeline.py data/raw/IGCSE/4PH1/2019/Jun/

Write-Host ""
Write-Host "Done! Check results above." -ForegroundColor Green
