#!/usr/bin/env python3

"""
🏥 ADVANCED HEALTHCARE CRM BOT v2.0 - Full Pipeline
✅ Scrape → Clean → Score → Outreach → Sheets (Daily)
✅ Render 24/7 + Lead Gen + AI Scoring + Email Outreach
✅ No breaking existing upload/schedule workflow
"""


import os
import sys
import asyncio
import argparse
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List
import json
import logging
from dataclasses import dataclass
from enum import Enum

try:
    import gspread
    from google.oauth2.service_account import Credentials
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.cron import CronTrigger
    from modules.lead_scraper import LeadScraper
    from modules.ai_scoring import score_leads
    from modules.outreach import send_intro_emails
except ImportError as e:
    print(f"❌ Missing dep: pip install -r requirements.txt")
    sys.exit(1)

# ========================================
# CONFIGURATION - PRODUCTION READY
# ========================================
@dataclass
class Config:
    SHEET_ID: str = os.getenv('GOOGLE_SHEET_ID', "1Ue3UXj-HYfJMSipy_oJ3wsUEKX9FuJsvZw50b2GrV1o")
    CREDS_FILES: List[str] = None
    DATA_DIR: Path = Path("data")
    LOG_DIR: Path = Path("logs")
    WORKSHEET_NAMES = {
        'leads': 'Doctor Leads',
        'followups': 'Follow-up Tracking', 
        'summary': 'Upload Summary'
    }
    
    def __post_init__(self):
        self.CREDS_FILES = ['data/credentials.json', 'data/google_credentials.json', 'credentials.json']
        self.DATA_DIR.mkdir(exist_ok=True)
        self.LOG_DIR.mkdir(exist_ok=True)
        
        # CRM Columns
        self.LEAD_COLUMNS = [
            'Doctor Name', 'Specialty', 'Hospital/Clinic', 'City', 'Phone', 
            'Email', 'Website', 'Source', 'Lead Status', 'Score', 'Last Contact',
            'Next Followup', 'Notes', 'Source URL', 'Timestamp'
        ]
        
        self.setup_logging()

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(self.LOG_DIR / 'crm_automation.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('HealthcareCRM')

config = Config()

class LeadStatus(Enum):
    NEW = "🆕 New"
    CONTACTED = "📞 Contacted"
    FOLLOWUP = "⏳ Follow-up Needed"
    WON = "✅ Converted"
    LOST = "❌ No Response"

# ========================================
# CORE CRM SYSTEM
# ========================================
class HealthcareCRM:
    def __init__(self):
        self.creds_file = self.find_credentials()
        self.client = None
        self.gc = None
        
    def find_credentials(self) -> str:
        """Find credentials file"""
        for creds_file in config.CREDS_FILES:
            creds_path = config.DATA_DIR / creds_file
            if creds_path.exists():
                print(f"✅ Credentials: {creds_file}")
                return str(creds_path)
        print("❌ Create credentials.json from Google Cloud Console")
        sys.exit(1)
    
    def connect_sheets(self) -> gspread.Spreadsheet:
        """Connect and setup worksheets"""
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        
        creds = Credentials.from_service_account_file(self.creds_file, scopes=scope)
        self.client = gspread.authorize(creds)
        self.gc = self.client.open_by_key(config.SHEET_ID)
        
        # Auto-create worksheets
        for name in config.WORKSHEET_NAMES.values():
            try:
                self.gc.add_worksheet(title=name, rows=1000, cols=20)
            except gspread.WorksheetNotFound:
                pass
        
        print("✅ All worksheets ready")
        return self.gc
    
    def ensure_crm_columns(self, worksheet):
        """Add CRM columns if missing"""
        headers = worksheet.row_values(1)
        missing_cols = [col for col in config.LEAD_COLUMNS if col not in headers]
        if missing_cols:
            worksheet.update('A1', config.LEAD_COLUMNS)
            print(f"✅ Added columns: {missing_cols}")
    
    def smart_deduplicate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Phone + Email deduplication with scoring"""

        # Clean phone/email (robust to missing columns)
        df['Phone'] = df.get('Phone', pd.Series(dtype=str)).fillna('')
        df['Email'] = df.get('Email', pd.Series(dtype=str)).fillna('')
        df['Doctor Name'] = df.get('Doctor Name', pd.Series(dtype=str)).fillna('')
        df['Phone_Clean'] = df['Phone'].str.replace(r'[^0-9+]', '', regex=True)
        df['Email_Clean'] = df['Email'].str.lower()

        
        # Dedupe priority: Email > Phone > Name
        df['dup_key'] = df['Email_Clean'].fillna(df['Phone_Clean']).fillna(df['Doctor Name'])
        df = df.drop_duplicates('dup_key', keep='first')
        
        # Lead scoring
        df['Score'] = 0
        df.loc[df['Email'].notna(), 'Score'] += 50
        df.loc[df['Phone'].notna(), 'Score'] += 30
        df.loc[df['Website'].notna(), 'Score'] += 20
        
        df['Lead Status'] = LeadStatus.NEW.value
        df['Timestamp'] = pd.Timestamp.now()
        df['Last Contact'] = ''
        df['Next Followup'] = (pd.Timestamp.now() + timedelta(days=3)).strftime('%Y-%m-%d')
        df['Notes'] = ''
        
        return df[config.LEAD_COLUMNS]
    
    def upload_leads(self, file_path: str):
        """Full CRM upload pipeline"""
        gc = self.connect_sheets()
        leads_ws = gc.worksheet(config.WORKSHEET_NAMES['leads'])
        

        # Load data with validation
        if not Path(file_path).exists():
            config.logger.error(f"❌ Missing file: {file_path}")
            return
        df = pd.read_excel(file_path, engine='openpyxl') if file_path.endswith('.xlsx') else pd.read_csv(file_path)
        print(f"📊 Loaded {len(df)} raw leads")
        
        # CRM transformation
        df_crm = self.smart_deduplicate(df)
        print(f"✅ Processed {len(df_crm)} CRM-ready leads")
        
        # Ensure columns
        self.ensure_crm_columns(leads_ws)
        
        # Dedupe with sheet
        records = leads_ws.get_all_records()
        existing_phones = {r.get('Phone', '') for r in records}
        existing_emails = {r.get('Email', '') for r in records}
        
        new_rows = []
        for _, row in df_crm.iterrows():
            if row['Phone'] not in existing_phones and row['Email'] not in existing_emails:
                new_rows.append(row.tolist())
        
        if new_rows:
            leads_ws.append_rows(new_rows)
            print(f"✅ UPLOADED {len(new_rows)} NEW DOCTOR LEADS")
            
            # Log summary
            summary_ws = gc.worksheet(config.WORKSHEET_NAMES['summary'])
            summary_row = [datetime.now().strftime('%Y-%m-%d %H:%M'), len(new_rows), len(df_crm), file_path]
            summary_ws.append_row(summary_row)
        else:
            print("ℹ️ No new leads (all exist)")
        
        print("🎉 CRM UPDATE COMPLETE!")
    
    async def full_pipeline(self):
        """Full daily workflow: scrape → clean → score → outreach → upload"""
        from modules.lead_scraper import LeadScraper
        from modules.ai_scoring import score_leads
        from modules.outreach import send_intro_emails
        
        print("🚀 Step 1/5: Scraping new leads...")
        scraper = LeadScraper()
        new_leads = await scraper.scrape_daily(limit=20)
        scraper.append_to_master(new_leads)
        
        print("🚀 Step 2/5: Cleaning & Dedupe...")
        df = pd.read_excel('data/doctor_leads_master.xlsx', engine='openpyxl')
        df_clean = self.smart_deduplicate(df)
        
        print("🚀 Step 3/5: AI Scoring...")
        df_scored = score_leads(df_clean)
        
        print("🚀 Step 4/5: Outreach...")
        df_outreach = send_intro_emails(df_scored)
        df_outreach.to_excel('data/doctor_leads_master.xlsx', index=False, engine='openpyxl')
        
        print("🚀 Step 5/5: Sheets Upload...")
        self.upload_leads('data/doctor_leads_master.xlsx')
        print("🎉 Full Pipeline Complete!")
    
    def schedule_daily(self):
        """Daily automation - now full pipeline"""

        scheduler = BlockingScheduler()
        scheduler.daemon = True
        scheduler.add_job(
            func=lambda: asyncio.run(self.full_pipeline()),
            trigger=CronTrigger(hour=9, minute=0),
            id='daily_pipeline',
            name='Daily Full CRM Pipeline'
        )
        print("⏰ Advanced scheduler started (Full pipeline daily 9AM)")
        scheduler.start()

def main():
    try:
        parser = argparse.ArgumentParser(description="Healthcare CRM Automation")
        parser.add_argument('--file', '-f', required=False, default='data/doctor_leads_master.xlsx')
        parser.add_argument('--schedule', '-s', action='store_true', help='Start daily scheduler')
        args = parser.parse_args()
        
        crm = HealthcareCRM()
        
        if args.schedule:
            crm.schedule_daily()
        else:
            crm.upload_leads(args.file)
    except Exception as e:
        logging.error(f"🚨 CRM Bot Error: {e}")
        print(f"🚨 Error: {e}")
        sys.exit(1)

