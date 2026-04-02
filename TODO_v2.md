# Global Doctor Lead Scraper Pro v2 - Development Plan

## Objective
Production scraper for 5000+ global doctor leads (India + International) with append Excel, scheduler, async, multi-format export.

## Information Gathered
- Existing scraper structure
- Dependencies installed (pandas 3.0.1, selenium 4.41.0, etc)
- Current dir: d:/leadscraper

## Plan
1. **Folder Structure** (create dirs/files)
```
leadscraper/
├── config/
│   ├── cities.py (India/global cities list)
│   ├── specialties.py
│   └── settings.py
├── scrapers/
│   ├── google_scraper.py
│   ├── duckduckgo_scraper.py  
│   ├── practo_scraper.py
│   └── dynamic_scraper.py
├── utils/
│   ├── validator.py
│   ├── deduper.py
│   └── exporter.py
├── logs/
├── data/
│   └── doctor_leads_master.xlsx
├── main.py
├── scheduler.py
├── requirements.txt (updated)
└── README.md
```

2. **Core Updates**
- Async HTTP (aiohttp)
- Multi-threading (ThreadPoolExecutor)
- DuckDuckGo search
- Global cities list (100+ cities)
- Append Excel logic
- CSV/JSON export
- Scheduler (APScheduler daily)

3. **Data Pipeline**
```
Cities list → Generate queries → Async search → Multi-thread scrape → Validate → Dedupe → Append Excel → Telegram
```

## TODO Steps
- [ ] Step 1: Create folder structure + city lists
- [ ] Step 2: Async scrapers (aiohttp + DuckDuckGo)
- [ ] Step 3: Multi-thread processing
- [ ] Step 4: Advanced validation/dedupe
- [ ] Step 5: Multi-format exporter (append Excel)
- [ ] Step 6: Telegram progress updates
- [ ] Step 7: Daily scheduler
- [ ] Step 8: Update README + test run

Ready to build v2?

