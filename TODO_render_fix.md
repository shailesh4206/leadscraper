# Render APScheduler Fix - TODO Steps

## Plan Breakdown
- [x] Step 1: Fix APScheduler error handling in fixed_google_sheet_uploader_v2.py (add EVENT_JOB_ERROR listener)
- [x] Step 2: Optionally fix same in lead_scraper_bot.py (bot_ready.py was clean)
- [x] Step 3: Test locally: python fixed_google_sheet_uploader_v2.py --schedule (Ctrl+C after startup) - No AttributeError (SHEET_ID missing locally expected, scheduler starts fine)
- [ ] Step 4: Commit changes and git push (Render auto-deploys)
- [ ] Step 5: Check Render logs for success
- [x] Step 6: Update this TODO with status - APScheduler AttributeError FIXED
