#!/usr/bin/env python3
\"\"\" 
Vectorax Healthcare CRM Lead Bot - Render 24/7 Ready
Full cycle: Scrape → Clean Phones → Dedupe Upload → Report
Run: python bot_ready.py [--test | --force-upload | --schedule]
\"\"\"

import argparse
import sys
import os
import json
import asyncio
from datetime import datetime
from pathlib import Path
import pandas as pd
import logging
from tenacity import retry
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False

# Graceful imports
try:
    from doctor_scraper_pro import GlobalDoctorScraper
    SCRAPER_AVAILABLE = True
except:
    SCRAPER_AVAILABLE = False

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSHEET_AVAILABLE = True
except ImportError:
    GSHEET_AVAILABLE = False

SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
if not SHEET_ID:
    print('❌ Set GOOGLE_SHEET_ID env var')
    sys.exit(1)

def get_credentials_file():
    env_creds = os.getenv('GOOGLE_CREDENTIALS_JSON')
    if env_creds:
        Path('data').mkdir(exist_ok=True)
        creds_file = Path('data') / 'credentials.json'
        with open(creds_file, 'w') as f:
            json.dump(json.loads(env_creds), f, indent=2)
        print(f'✅ Credentials from env -> {creds_file}')
        return str(creds_file)
    raise ValueError('❌ Set GOOGLE_CREDENTIALS_JSON or credentials.json')

def setup_logging():
    Path('logs').mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] BOT: %(message)s',
        handlers=[logging.FileHandler('logs/bot_health.log'), logging.StreamHandler()])
    return logging.getLogger('BotReady')

def clean_phones(df):
    \"\"\"Integrate phone_cleaner logic\"\"\"
    COUNTRY_RULES = {
        'India': {'lengths': [10], 'code': '+91'},
        'USA': {'lengths': [10], 'code': '+1'},
        'UK': {'lengths': [10,11], 'code': '+44'},
        'Australia': {'lengths': [9], 'code': '+61'}
    }
    def clean_phone(phone, country='India'):
        if pd.isna(phone): return ''
        phone_str = str(phone).strip().rstrip('.0')
        if phone_str.lower() == 'nan': return ''
        digits = re.sub(r'\\D', '', phone_str)
        if len(digits) < 7: return ''
        # Add country code if valid length
        rule = COUNTRY_RULES.get(country, COUNTRY_RULES['India'])
        if len(digits) in rule['lengths']:
            return rule['code'] + digits
        return ''
    import re
    df['Phone Number'] = df.apply(lambda row: clean_phone(row['Phone Number'], row.get('Country', 'India')), axis=1)
    return df

@retry
def upload_dedupe(df, logger):
    \"\"\"Read sheet, append new unique leads\"\"\"
    creds_file = get_credentials_file()
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file(creds_file, scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).sheet1
    
    # Get existing
    records = sheet.get_all_records()
    existing_emails = {r.get('Email Address', '') for r in records}
    existing_phones = {r.get('Phone Number', '') for r in records}
    
    new_rows = []
    for _, row in df.iterrows():
        if row['Email Address'] not in existing_emails and row['Phone Number'] not in existing_phones:
            new_rows.append(row.tolist())
    
    if new_rows:
        sheet.append_rows(new_rows)
        logger.info(f'✅ Appended {len(new_rows)} new unique leads')
        return len(new_rows)
    logger.info('ℹ️ No new unique leads')
    return 0

def scrape_new_leads(logger, max_leads=5):
    \"\"\"Fetch new leads if scraper available\"\"\"
    if not SCRAPER_AVAILABLE:
        logger.warning('Scraper not available')
        return pd.DataFrame()
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        scraper = GlobalDoctorScraper()
        urls = loop.run_until_complete(scraper.google_search('Cardiologist Mumbai contact'))
        leads = []
        for url in urls[:max_leads]:
            lead = loop.run_until_complete(scraper.scrape_page(url))
            if lead:
                leads.append(lead)
        df = pd.DataFrame(leads)
        logger.info(f'📈 Scraped {len(df)} new leads')
        return df
    except Exception as e:
        logger.error(f'Scrape error: {e}')
        return pd.DataFrame()

def generate_report(logger, sheet_rows_before, sheet_rows_after, new_excel_rows, appended_rows):
    report = f"""BOT HEALTH REPORT - {datetime.now()}
✅ Credentials: LOADED
✅ Sheet accessed: {SHEET_ID} ({sheet_rows_before} → {sheet_rows_after} rows)
📊 Excel: {new_excel_rows} rows processed
➕ Appended: {appended_rows} new unique leads
📱 Phone cleaning: Applied to all
{'✅ Scraper: OK' if SCRAPER_AVAILABLE else '⚠️ Scraper: Missing'}
Status: ACTIVE 24/7"""
    Path('logs/bot_health_report.txt').write_text(report)
    logger.info('Report saved: logs/bot_health_report.txt')
    print(report)

def bot_cycle(logger):
    logger.info('=== BOT CYCLE START ===')
    # Scrape new
    df_new = scrape_new_leads(logger)
    if not df_new.empty:
        df_new = clean_phones(df_new)
        excel_path = Path('data/doctor_leads_master.xlsx')
        if excel_path.exists():
            df_existing = pd.read_excel(excel_path)
            df_all = pd.concat([df_existing, df_new]).drop_duplicates()
        else:
            df_all = df_new
        df_all.to_excel(excel_path, index=False)
    else:
        excel_path = Path('data/doctor_leads_master.xlsx')
        df_all = pd.read_excel(excel_path) if excel_path.exists() else pd.DataFrame()
    
    # Upload
    if GSHEET_AVAILABLE:
        sheet_rows_before = 0
        creds_file = get_credentials_file()
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_file(creds_file, scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID).sheet1
        sheet_rows_before = sheet.row_count
        appended = upload_dedupe(df_all, logger)
        sheet_rows_after = sheet.row_count
        generate_report(logger, sheet_rows_before, sheet_rows_after, len(df_all), appended)
    logger.info('=== BOT CYCLE END ===')

def main():
    parser = argparse.ArgumentParser(description='Healthcare Lead Bot')
    parser.add_argument('--test', action='store_true', help='Test mode')
    parser.add_argument('--force-upload', action='store_true', help='Upload all ignoring dedupe')
    parser.add_argument('--schedule', action='store_true', help='Run 24/7 scheduler')
    args = parser.parse_args()
    
    logger = setup_logging()
    
    if args.test:
        bot_cycle(logger)
        print('✅ Test complete')
        return
    
    if args.force_upload:
        # Similar but no dedupe
        logger.info('Force upload mode')
        excel_path = Path('data/doctor_leads_master.xlsx')
        if excel_path.exists():
            df = pd.read_excel(excel_path)
            creds_file = get_credentials_file()
            scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
            creds = Credentials.from_service_account_file(creds_file, scopes=scope)
            client = gspread.authorize(creds)
            sheet = client.open_by_key(SHEET_ID).sheet1
            sheet.append_rows(df.values.tolist())
            logger.info(f'Force uploaded {len(df)} rows')
        return
    
    if args.schedule and SCHEDULER_AVAILABLE:
        scheduler = BackgroundScheduler()
        scheduler.add_job(bot_cycle, 'interval', minutes=30, args=[logger])
        scheduler.start()
        logger.info('24/7 Scheduler started (30min cycles). Press Ctrl+C to stop.')
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            scheduler.shutdown()
    else:
        bot_cycle(logger)

if __name__ == '__main__':
    main()

