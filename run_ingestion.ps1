# GradeMax Phase 2 - Run Ingestion
# Sets environment variables and runs the ingestion pipeline

# Set environment variables
$env:GEMINI_API_KEY = "AIzaSyBsqRLYDl7IsdboZzjoyM7n9EskKZTH57A"
$env:NEXT_PUBLIC_SUPABASE_URL = "https://tybaetnvnfgniotdfxze.supabase.co"
$env:NEXT_PUBLIC_SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR5YmFldG52bmZnbmlvdGRmeHplIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTcwOTkzMTcsImV4cCI6MjA3MjY3NTMxN30.QRxEmsZFtp0LHFycU6pljuFqJineV8AcTpjo4nBAYes"

Write-Host "🚀 Starting ingestion pipeline..." -ForegroundColor Green
Write-Host ""

# Run ingestion
python scripts/ingest_pipeline.py data/raw/IGCSE/4PH1/2019/Jun/

Write-Host ""
Write-Host "✅ Done! Check results above." -ForegroundColor Green
