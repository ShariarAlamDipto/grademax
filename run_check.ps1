# Load environment variables from .env.local
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

Write-Host "Running verification script..."
python scripts/debug_pdf_urls.py
