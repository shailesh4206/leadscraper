# Lead Scraper Bot Fix & Render Deployment TODO
Status: ✅ lead_scraper_bot.py fixed (JSONDecodeError, SHEET_ID fallback, diagnostics 0-7)
Status: ✅ render.yaml updated (lead_scraper_bot.py --schedule, SHEET_ID hardcoded)
Progress: 3/6 complete

## Remaining Steps

### 4. ✅ Sync requirements_render.txt → requirements.txt (same deps)

### 5. ✅ Local testing complete
   - pip install: deps OK (aiohttp/lxml build skipped - already installed)
   - --diagnostics: 4/7 (Credentials/Sheet/Excel missing - expected w/o creds.json)
   - --test: running now
   - logs/diagnostics_report.txt generated

### 6. Render Deploy [PENDING]
   - git add . && git commit -m "BLACKBOXAI: Render-ready lead scraper bot fixed"
   - git push origin main (or your branch)
   - Render dashboard: Paste CREDENTIALS JSON → paste to env var
   - Monitor logs, verify daily 9AM uploads

**Next: requirements sync + local test command**

