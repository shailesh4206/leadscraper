# 1️⃣ Set environment variables for Google Sheet (replace with your actual IDs and paths)
$env:GOOGLE_SHEET_ID="1Ue3UXj-HYfJMSipy_oJ3wsUEKX9FuJsvZw50b2GrV1o"
$env:GOOGLE_CREDENTIALS_PATH="D:\leadscraper\service_account.json"

# 2️⃣ Run Python bot safely with UTF-8 encoding
python -X utf8 lead_scraper_bot.py --diagnostics | Out-Host

# 3️⃣ Capture errors and redirect them to a log file
python -X utf8 lead_scraper_bot.py --diagnostics 2> error_log.txt | Out-Host

# 4️⃣ Optional: View error log if exists
if (Test-Path error_log.txt) {
    Write-Host "❌ Errors captured in error_log.txt"
    Get-Content error_log.txt
} else {
    Write-Host "✅ No errors detected"
}

