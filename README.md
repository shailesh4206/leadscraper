# Vectorax Doctor Lead Scraper Pro 🚀

Production-ready Python bot that extracts verified doctor leads (email/phone) from public sources.

## Features
✅ Google search automation  
✅ Public sources: Practo, JustDial, hospitals, directories  
✅ Smart validation (removes fakes/duplicates)  
✅ Selenium for dynamic JS sites  
✅ Telegram notifications + Excel export  
✅ Windows/Cloud ready (Render)  
✅ Rate limiting, retries, logging  

## Quick Start (Windows)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure (edit config.py)
# CITY = "Mumbai"
# SPECIALTY = "Dentist" 
# SEARCH_LIMIT = 50
# TELEGRAM_TOKEN = "your_bot_token"
# TELEGRAM_CHAT_ID = "your_chat_id"

# 3. Run scraper
python scraper.py
```

**Output**: `vectorax_verified_doctor_leads.xlsx` + Telegram file delivery 📱

## Config Options (config.py)
```
CITY = "Pune"           # Target city
SPECIALTY = "Cardiologist"  # Doctor specialty  
SEARCH_LIMIT = 100      # Max results
HEADLESS_MODE = True    # Hide Chrome browser
TIMEOUT = 30           # Page timeout
MAX_RETRIES = 3        # Failed request retries
```

## Data Fields Extracted
| Column | Description |
|--------|-------------|
| Doctor Name | Extracted via ML heuristics |
| Specialty | Configured filter |
| City | Configured filter |
| Hospital | Clinic/Hospital name |
| Email | Validated emails only |
| Phone | Formatted +91 numbers |
| Website | Doctor profile |
| Source URL | Original page |

## Validation Rules
- ✅ Email regex + domain blacklist
- ✅ Phone: 10+ digits, India format
- ✅ Deduplication by name/email/phone  
- ✅ Must have email **OR** phone to save
- ✅ Removes example@test.com placeholders

## Render Deployment - Healthcare CRM Bot ✅

**Background Worker (24/7 Scheduler)**

Uses `render.yaml` (pre-configured):
```
services:
  - type: worker
    name: healthcare-crm-bot  
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: python healthcare_crm_automation.py --schedule
```

### Deploy Steps:
1. ✅ Git commit/push (data/ files optional, recreated)
2. Render.com → New → Background Worker
3. Connect GitHub repo → Auto-deploy  
4. (Optional) Env Var: `GOOGLE_SHEET_ID`
5. ✅ Monitor Render logs: "⏰ Daily scheduler started"

**Runs daily 9AM uploads + full logging + auto-restart**

## Screenshots
```
📱 Telegram delivery:
🎉 Vectorax Complete!
✅ 23 Cardiologist leads in Pune
📊 vectorax_verified_doctor_leads.xlsx [FILE]
```

## Troubleshooting
```
ChromeDriver: webdriver-manager auto-installs
Google blocks: Rotate user-agents (built-in)
No leads: Increase SEARCH_LIMIT=200
Telegram fail: Check config.py tokens
```

## Sources (Public Only)
- Google search results
- Practo.com public profiles  
- JustDial.com listings
- Hospital websites
- Medical directories

**⚠️ Respect robots.txt | Rate limits | Public data only**

---

**Made with ❤️ by BLACKBOXAI** | Production ready since 2024

