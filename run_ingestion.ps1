# GradeMax Phase 2 - Run Ingestion
# Sets environment variables and runs the ingestion pipeline

# Set environment variables
$env:GEMINI_API_KEY = "REDACTED"
$env:NEXT_PUBLIC_SUPABASE_URL = "https://tybaetnvnfgniotdfxze.supabase.co"
$env:NEXT_PUBLIC_SUPABASE_ANON_KEY = "REDACTED"

Write-Host "🚀 Starting ingestion pipeline..." -ForegroundColor Green
Write-Host ""

# Run ingestion
python scripts/ingest_pipeline.py data/raw/IGCSE/4PH1/2019/Jun/

Write-Host ""
Write-Host "✅ Done! Check results above." -ForegroundColor Green
