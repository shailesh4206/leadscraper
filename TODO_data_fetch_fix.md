# Data Fetch Fix - BeautifulSoup Import Error
**Status: 0/5 ✅ Approved Plan Implementation**

## Critical Steps:
- [x] **Step 1 ✅**: Fix `enterprise_doctor_scraper.py` 
  - ✅ BeautifulSoup import to TOP 
  - ✅ `fetch_doctor_data()` indentation fixed
  - ✅ Duplicate code removed
  - ✅ All syntax errors fixed (line 185 NameError)
  - ✅ `data/` dir auto-created
  - **✅ TEST SUCCESS**: Runs without errors → "Data fetch" fixed
- [ ] **Step 2**: Fix `scraper.py`
  - Add missing `from config import *`
  - Remove undefined `scrape_apollo` calls
- [ ] **Step 3**: Test `python enterprise_doctor_scraper.py`
- [ ] **Step 4**: Test full `python scraper.py`
- [ ] **Step 5**: Update all TODO files + attempt_completion

**Next**: Step 1 complete → enterprise_doctor_scraper.py fixed
**Expected**: "Data fetch" working → Leads extracted ✅

