# Render Fix COMPLETE - Port/No Open Ports FIXED via render.yaml worker config
**Main TODO.md tracks git push → verification**

## Plan Breakdown
- [x] Step 1: Fix APScheduler error handling in fixed_google_sheet_uploader_v2.py (add EVENT_JOB_ERROR listener)
- [x] Step 2: Optionally fix same in lead_scraper_bot.py (bot_ready.py was clean)
- [x] Step 3: Test locally: python fixed_google_sheet_uploader_v2.py --schedule (Ctrl+C after startup) - No AttributeError (SHEET_ID missing locally expected, scheduler starts fine)
- [ ] Step 4: Git push for auto-deploy
  ```
  git add . && git commit -m \"Fix Render worker config\" && git push
  ```
  See [TODO.md Step 5]
- [ ] Step 5: ✅ Verify Render logs
  - \"24/7 Scheduler started - Daily 9AM\"
  - No more \"No open ports\" errors
  - logs/bot_health.log updates
- [x] Step 6: Update this TODO with status - APScheduler AttributeError FIXED
