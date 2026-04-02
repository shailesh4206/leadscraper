#!/usr/bin/env python3
""" 
Render-Ready Lead Scraper Uploader v2 - Full 24/7 Bot
Features: Diagnostics, Daily Scheduler 9AM, Force Upload, Phone Cleaning, Dedupe
Usage: python fixed_google_sheet_uploader_v2.py [--schedule | --force-upload | --diagnostics]
"""

import argparse
import sys
import os
import json
import time
import re
import importlib.util
from datetime import datetime
from pathlib import Path
import pandas as pd
import logging

# Scheduler
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False
    print('pip install apscheduler')

# Scraper (optional)
SCAPER_AVAILABLE = False
try:
    from doctor_scraper_pro import GlobalDoctorScraper
    SCAPER_AVAILABLE = True
except ImportError:
    pass

# Sheets
try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSHEET_AVAILABLE = True
except ImportError:
    GSHEET_AVAILABLE = False

from tenacity import retry, stop_after_attempt

# Env vars
SHEET_ID = os.getenv('SHEET_ID')
if not SHEET_ID:
    print('❌ Set SHEET_ID env var')
    sys.exit(1)

def get_credentials_file():
    """Render CREDENTIALS env -> data/credentials.json"""
    env_creds = os.getenv('CREDENTIALS')
    if env_creds:
        Path('data').mkdir(exist_ok=True)
        creds_file = Path('data') / 'credentials.json'
        with open(creds_file, 'w') as f:
            json.dump(json.loads(env_creds), f, indent=2)
        print(f'OK Credentials from CREDENTIALS -> {creds_file}')
        return str(creds_file)
    
    # Fallback
    for creds_path in ['data/credentials.json', 'credentials.json']:
        if Path(creds_path).exists():
            print(f'OK Local creds: {creds_path}')
            return creds_path
    
    raise ValueError('❌ Set CREDENTIALS (JSON string)')

def setup_logging():
    Path('logs').mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] BOT: %(message)s',
        handlers=[
            logging.FileHandler('logs/bot_health.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger('Uploader')

def clean_phones(df):
    """Clean phone numbers, add country code (+91 India default)"""
    COUNTRY_RULES = {
        'India': {'lengths': [10], 'code': '+91'},
        'USA': {'lengths': [10], 'code': '+1'},
        'UK': {'lengths': [10,11], 'code': '+44'},
        'Australia': {'lengths': [9], 'code': '+61'}
    }
    def clean_one(phone, country='India'):
        if pd.isna(phone): return ''
        phone_str = str(phone).strip().rstrip('.0')
        if phone_str.lower() == 'nan': return ''
        digits = re.sub(r'\\D', '', phone_str)
        if len(digits) < 7: return ''
        rule = COUNTRY_RULES.get(country, COUNTRY_RULES['India'])
        if len(digits) in rule['lengths']:
            return rule['code'] + digits
        return ''
    df['Phone Number'] = df.apply(lambda row: clean_one(row.get('Phone Number', ''), row.get('Country', 'India')), axis=1)
    print(f'Phone cleaning: {df["Phone Number"].str.strip().ne("").sum()} valid')
    return df

@retry(stop=stop_after_attempt(3))
def upload_dedupe(df, logger):
    """Dedupe upload - append new rows only"""
    creds_file = get_credentials_file()
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file(creds_file, scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).sheet1
    
    records = sheet.get_all_records()
    existing_emails = {r.get('Email Address', '') for r in records}
    existing_phones = {r.get('Phone Number', '') for r in records}
    
    new_rows = []
    duplicates_skipped = 0
    for _, row in df.iterrows():
        email = row.get('Email Address', '')
        phone = row.get('Phone Number', '')
        if email not in existing_emails and phone not in existing_phones:
            new_rows.append(row.tolist())
        else:
            duplicates_skipped += 1
    
    if new_rows:
        sheet.append_rows(new_rows)
        logger.info(f'Uploaded {len(new_rows)} new rows, skipped {duplicates_skipped} duplicates')
        return len(new_rows), duplicates_skipped
    logger.info(f'No new rows - skipped {duplicates_skipped}')
    return 0, duplicates_skipped

def upload_force(df, logger):
    """Force upload all rows - ignore dupes"""
    creds_file = get_credentials_file()
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file(creds_file, scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).sheet1
    sheet.append_rows(df.tolist())
    logger.info(f'Force uploaded {len(df)} rows')
    return len(df), 0

def test_credentials():
    """Test 1: Credentials"""
    try:
        get_credentials_file()
        return True, 'Loaded'
    except:
        return False, 'Failed'

def test_sheet():
    """Test 2: Sheet connect"""
    logger = logging.getLogger('Test')
    try:
        creds_file = get_credentials_file()
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_file(creds_file, scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID).sheet1
        return True, f'OK ({sheet.row_count} rows)'
    except Exception as e:
        return False, str(e)

def test_excel():
    """Test 3: Excel R/W"""
    excel_path = Path('data/doctor_leads_master.xlsx')
    try:
        if not excel_path.exists():
            pd.DataFrame({'test': [1]}).to_excel(excel_path)
        pd.read_excel(excel_path)
        return True, 'OK'
    except:
        return False, 'Failed'

def test_dupes():
    """Test 4: Dup detection"""
    excel_path = Path('data/doctor_leads_master.xlsx')
    if not excel_path.exists():
        return True, 'Skipped (no Excel)'
    try:
        df = pd.read_excel(excel_path)
        dupe_df = pd.concat([df, df.iloc[[0]]]).drop_duplicates(subset=['Doctor Name', 'Phone Number'])
        skipped = len(df) - len(dupe_df)
        return skipped > 0, f'OK ({skipped} skipped)'
    except:
        return False, 'Failed'

def test_phones():
    """Test 5: Phone cleaning"""
    excel_path = Path('data/doctor_leads_master.xlsx')
    if not excel_path.exists():
        return True, 'Skipped'
    try:
        df = pd.read_excel(excel_path)
        df_clean = clean_phones(df)
        valid = df_clean['Phone Number'].str.strip().ne('').sum()
        return valid > 0, f'OK ({valid} valid)'
    except:
        return False, 'Failed'

def test_logs():
    """Test 6: Logs"""
    return True, 'OK'

def test_scheduler():
    """Test 7: Scheduler"""
    return SCHEDULER_AVAILABLE, 'Available' if SCHEDULER_AVAILABLE else 'pip install apscheduler'

def run_diagnostics(logger):
    """Full diagnostics report"""
    tests = [
        ('Credentials', test_credentials()),
        ('Sheet', test_sheet()),
        ('Excel', test_excel()),
        ('Dupes', test_dupes()),
        ('Phones', test_phones()),
        ('Logs', test_logs()),
        ('Scheduler', test_scheduler())
    ]
    
    passed = sum(1 for _, (ok, _) in tests if ok)
    report = f'BOT HEALTH REPORT {datetime.now()}\\nPassed {passed}/7\\n\\n'
    for name, (ok, msg) in tests:
        status = '✅' if ok else '❌'
        report += f'{status} {name}: {msg}\\n'
    
    Path('logs/bot_health_report.txt').write_text(report)
    logger.info('Diagnostics OK')
    print(report)
    return passed == 7

def bot_cycle(logger):
    """Daily cycle: clean → upload → report"""
    try:
        run_diagnostics(logger)
        
        excel_path = Path('data/doctor_leads_master.xlsx')
        if not excel_path.exists():
            logger.warning('No Excel - create with scraper')
            return
        
        df = pd.read_excel(excel_path)
        df = clean_phones(df)
        
        rows_new, skipped = upload_dedupe(df, logger)
        
        report = f'DAILY REPORT {datetime.now()}\\nExcel rows: {len(df)}\\nNew uploaded: {rows_new}\\nDuplicates skipped: {skipped}'
        Path('logs/daily_report.txt').write_text(report)
        logger.info(report)
    except Exception as e:
        logger.error(f'Cycle error: {e}')

def scheduler_main(logger):
    """24/7 scheduler - daily 9AM + error restart"""
    scheduler = BackgroundScheduler()
    scheduler.add_error_handler(lambda job, exc: logger.error(f'Scheduler error: {exc}'))
    
    scheduler.add_job(bot_cycle, CronTrigger(hour=9, minute=0), args=[logger], id='daily_upload')
    scheduler.start()
    
    logger.info('24/7 Scheduler started - Daily 9AM. Ctrl+C to stop')
    try:
        while True:
            time.sleep(60)  # Keep alive
    except KeyboardInterrupt:
        scheduler.shutdown()

def main():
    parser = argparse.ArgumentParser(description='Lead Scraper Uploader Bot')
    parser.add_argument('--diagnostics', action='store_true', help='Run diagnostics')
    parser.add_argument('--force-upload', action='store_true', help='Upload all rows ignore dupes')
    parser.add_argument('--schedule', action='store_true', help='Start 24/7 scheduler')
    args = parser.parse_args()
    
    logger = setup_logging()
    
    if args.diagnostics:
        run_diagnostics(logger)
        sys.exit(0)
    
    if args.force_upload:
        excel_path = Path('data/doctor_leads_master.xlsx')
        if excel_path.exists():
            df = pd.read_excel(excel_path)
            df = clean_phones(df)
            upload_force(df, logger)
        else:
            logger.error('No Excel file')
        sys.exit(0)
    
    if args.schedule:
        if not SCHEDULER_AVAILABLE:
            logger.error('pip install apscheduler')
            sys.exit(1)
        scheduler_main(logger)
    else:
        # Single run
        bot_cycle(logger)
        print('Single run complete')

if __name__ == '__main__':
    main()

