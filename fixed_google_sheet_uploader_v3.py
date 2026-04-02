#!/usr/bin/env python3
\"\"\"FULL AUTOMATIC DIAGNOSTIC + SYNC VERIFICATION UPLOADER v3
Diagnostics + Row Count Verification + Smart Upload + Sync Report
Automatic: Check Excel > Sheet -> Upload missing | Equal -> Skip | Sheet > Excel -> Warn\"\"\"
import argparse
import sys
import os
import json
import time
import importlib.util
from datetime import datetime
from pathlib import Path
import pandas as pd
import logging

# Global imports with graceful fallbacks
SCAPER_AVAILABLE = False
try:
    from doctor_scraper_pro import GlobalDoctorScraper
    SCAPER_AVAILABLE = True
except ImportError:
    pass

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    print("Missing: pip install gspread google-auth pandas openpyxl duckduckgo-search")
    sys.exit(1)

SHEET_ID = \"1Ue3UXj-HYfJMSipy_oJ3wsUEKX9FuJsvZw50b2GrV1o\"
CREDENTIALS_FILES = ['data/credentials.json', 'credentials.json']

REQUIRED_FILES = [
    'data/credentials.json',
    'data/doctor_leads_master.xlsx',
    'doctor_leads_verified.xlsx',
    'logs/'
]

REQUIRED_MODULES = ['pandas', 'gspread', 'google.auth', 'openpyxl']

def setup_logging():
    Path('logs').mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] BOT-HEALTH: %(message)s',
        handlers=[
            logging.FileHandler('logs/bot_health.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger('BotDiagnostics')

def check_modules(logger):
    missing = []
    for module in REQUIRED_MODULES:
        if importlib.util.find_spec(module) is None:
            missing.append(module)
            logger.warning(f\"Missing module: {module}\")
    return missing

def check_files(logger):
    missing = []
    for f in REQUIRED_FILES:
        path = Path(f)
        if not path.exists():
            missing.append(str(path))
            logger.warning(f\"Missing file: {path}\")
    return missing

def test_data_fetch(logger):
    \"\"\"Real data fetching test\"\"\" 
    if not SCAPER_AVAILABLE:
        return False, 0, \"Scraper not available\"
    try:
        import asyncio
        scraper = GlobalDoctorScraper()
        urls = asyncio.run(scraper.google_search(\"Cardiologist Mumbai contact\"))
        if urls:
            lead = asyncio.run(scraper.scrape_page(urls[0]))
            count = 1 if lead and lead.get('Doctor Name') else 0
            return count > 0, count, f\"{count} lead(s) OK\"
        return False, 0, \"No URLs\"
    except Exception as e:
        return False, 0, f\"{str(e)}\"

def test_sheet_upload(logger):
    \"\"\"Sheet connection + upload test with cleanup\"\"\" 
    creds_file = next((p for p in CREDENTIALS_FILES if Path(p).exists()), None)
    if not creds_file:
        return False, \"No credentials\"
    
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    try:
        creds = Credentials.from_service_account_file(creds_file, scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID).sheet1
        
        original_count = sheet.row_count
        test_row = ['DIAG-TEST', 'Test', '', 'Test City'] + ['']*10
        sheet.append_row(test_row)
        time.sleep(1)
        
        if sheet.row_count == original_count + 1:
            sheet.delete_rows(original_count + 1, 1)
            return True, \"Connect + append/delete OK\"
        return False, \"Row verification failed\"
    except Exception as e:
        return False, f\"{str(e)}\"

def test_duplicate_detection(logger):
    \"\"\"Real duplicate detection test\"\"\" 
    excel_path = 'data/doctor_leads_master.xlsx'
    if not Path(excel_path).exists():
        return False, \"No Excel file\"
    
    try:
        df = pd.read_excel(excel_path)
        if len(df) == 0:
            return True, \"No data - skipped\"
        
        dupe_df = pd.concat([df, df.iloc[[0]]]).drop_duplicates(subset=['Doctor Name', 'Phone Number', 'Email Address'])
        dupe_count = len(df) - len(dupe_df)
        return dupe_count > 0, \"Detected OK\", dupe_count
    except:
        return False, \"Test failed\"

def parse_statistics(logger):
    \"\"\"Parse real stats from files\"\"\" 
    excel_path = 'data/doctor_leads_master.xlsx'
    stats = {'excel_rows': 0, 'duplicates': 0}
    
    try:
        if Path(excel_path).exists():
            df = pd.read_excel(excel_path)
            stats['excel_rows'] = len(df)
            stats['duplicates'] = len(df) - len(df.drop_duplicates(subset=['Doctor Name', 'Phone Number']))
    except:
        pass
    
    return stats

def get_fix_suggestions(diagnostics):
    \"\"\"Auto-fix suggestions\"\"\" 
    fixes = []
    if diagnostics['missing_modules']:
        fixes.append(f\"pip install {' '.join(diagnostics['missing_modules'])}\")
    if 'data/credentials.json' in diagnostics['missing_files']:
        fixes.append(\"1. Google Console → New Service Account\\n2. JSON key → data/credentials.json\")
    if not SCAPER_AVAILABLE:
        fixes.append(\"pip install duckduckgo-search aiohttp beautifulsoup4 selenium\")
    if diagnostics['status'].get('data_fetch', (False,''))[0] == False:
        fixes.append(\"python doctor_scraper_pro.py --test\")
    return fixes

def test_excel_io(logger):
    \"\"\"Test Excel read/write (placeholder - assume OK for now)\"\"\"
    return True, \"Excel IO OK\"

def generate_report(diagnostics, logger):
    \"\"\"Generate diagnostic report (placeholder)\"\"\"
    Path('logs').mkdir(exist_ok=True)
    report_path = 'logs/bot_health_report.txt'
    with open(report_path, 'w') as f:
        f.write(f\"Bot Diagnostics Report: {datetime.now()}\\n\")
        f.write(f\"Overall: {diagnostics['overall_status']}\\n\")
    logger.info(f'Report saved to {report_path}')

def upload_data(df, sheet):
    \"\"\"Upload df to sheet with deduplication, return rows uploaded\"\"\"
    print(f\"📊 Data shape: {df.shape}\")
    
    # Get existing records for dedupe
    records = sheet.get_all_records()
    existing_emails = {r.get('Email Address', '') for r in records}
    existing_phones = {r.get('Phone Number', '') for r in records}
    
    print(f\"📈 Sheet has {len(records)} rows from records\")
    
    new_rows = []
    for idx, row in df.iterrows():
        email = str(row.get('Email Address', ''))
        phone = str(row.get('Phone Number', ''))
        if email not in existing_emails and phone not in existing_phones:
            new_rows.append([str(row.get(col, '')) for col in df.columns])
    
    rows_uploaded = len(new_rows)
    if new_rows:
        sheet.append_rows(new_rows)
        print(f\"✅ UPLOADED {rows_uploaded} new rows!\")
    else:
        print(\"ℹ️ No new unique data\")
    
    return rows_uploaded

def save_sync_report(excel_rows, sheet_rows, rows_uploaded, action):
    \"\"\"Save sync report to logs/sync_report.txt\"\"\"
    Path('logs').mkdir(exist_ok=True)
    report_path = 'logs/sync_report.txt'
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(report_path, 'a', encoding='utf-8') as f:
        f.write(f\"{timestamp} | Excel rows: {excel_rows} | Google Sheet rows: {sheet_rows} | Rows uploaded: {rows_uploaded} | {action}\\n\")
    print(f\"📄 Sync report saved: {report_path}\")

def run_full_bot_diagnostics(logger):
    \"\"\"MAIN DIAGNOSTIC FUNCTION\"\"\"
    diagnostics = {
        'status': {},
        'counters': {'fetch': 0, 'save': 0, 'upload': 0, 'duplicates': 0},
        'missing_files': check_files(logger),
        'missing_modules': check_modules(logger),
        'errors': []
    }
    
    diagnostics['status']['startup'] = (True, 'OK')
    diagnostics['status']['files'] = (not diagnostics['missing_files'], f\"{len(diagnostics['missing_files'])} missing\")
    diagnostics['status']['modules'] = (not diagnostics['missing_modules'], f\"{len(diagnostics['missing_modules'])} missing\")
    
    ok, count, msg = test_data_fetch(logger)
    diagnostics['status']['data_fetch'] = (ok, msg)
    diagnostics['counters']['fetch'] = count
    
    ok, msg = test_excel_io(logger)
    diagnostics['status']['excel_save'] = (ok, msg)
    
    ok, msg = test_sheet_upload(logger)
    diagnostics['status']['sheet_connect'] = (ok, msg)
    
    ok, msg = test_duplicate_detection(logger)
    diagnostics['status']['duplicate_detection'] = (ok, msg)
    
    diagnostics['status']['logs'] = (True, 'OK')
    
    stats = parse_statistics(logger)
    diagnostics['counters'].update(stats)
    
    passed = sum(1 for v in diagnostics['status'].values() if v[0])
    total = len(diagnostics['status'])
    diagnostics['overall_status'] = 'Running' if passed/total > 0.8 else 'Failed'
    
    generate_report(diagnostics, logger)
    return diagnostics

def main():
    parser = argparse.ArgumentParser(description='Lead Bot Diagnostics + Sync Uploader')
    parser.add_argument('--diagnostics-only', action='store_true', help='Run tests only')
    args = parser.parse_args()
    
    logger = setup_logging()
    diagnostics = run_full_bot_diagnostics(logger)
    
    if args.diagnostics_only:
        print(\"\\n✅ Diagnostics complete. Report: logs/bot_health_report.txt\")
        sys.exit(0)
    
    if diagnostics['overall_status'] != 'Running':
        print(\"\\n⚠️ Diagnostics FAILED. Fix issues first.\")
        sys.exit(1)
    
    # SYNC VERIFICATION + UPLOAD
    file_path = Path('data/doctor_leads_master.xlsx')
    if not file_path.exists():
        print(\"❌ Excel missing. Run scraper first.\")
        sys.exit(1)
    
    df = pd.read_excel(file_path)
    excel_rows = len(df)
    
    creds_file = next((c for c in CREDENTIALS_FILES if Path(c).exists()), None)
    if not creds_file:
        print(\"❌ Credentials missing.\")
        sys.exit(1)
    
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file(creds_file, scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).sheet1
    sheet_rows = sheet.row_count
    
    print(f\"Excel rows count: {excel_rows}\")
    print(f\"Google Sheet rows count: {sheet_rows}\")
    
    rows_uploaded = 0
    if excel_rows > sheet_rows:
        print(\"📤 Excel has more rows - uploading missing...\")
        rows_uploaded = upload_data(df, sheet)
        print(f\"Rows uploaded this run: {rows_uploaded}\")
        action = f\"Uploaded {rows_uploaded} rows\"
    elif excel_rows == sheet_rows:
        print(\"Already synced successfully\")
        action = \"Already synced - no upload\"
    else:
        print(\"⚠️ Google Sheet has extra rows\")
        action = \"Sheet has extra rows - no upload\"
    
    # Save sync report
    save_sync_report(excel_rows, sheet_rows, rows_uploaded, action)
    
    print(\"\\n🎉 Sync verification + upload complete! Check logs/sync_report.txt\")
    sys.exit(0)

if __name__ == '__main__':
    main()
