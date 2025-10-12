# Load environment variables
$env:GEMINI_API_KEY = "REDACTED"
$env:NEXT_PUBLIC_SUPABASE_URL = "https://tybaetnvnfgniotdfxze.supabase.co"
$env:NEXT_PUBLIC_SUPABASE_ANON_KEY = "REDACTED"

Write-Host "Running verification script..."
python scripts/debug_pdf_urls.py
