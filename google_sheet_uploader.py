#!/usr/bin/env python3
"""
Standalone Google Sheet uploader for Vectorax Doctor Scraper
Use: python google_sheet_uploader.py --file data/doctor_leads_master.xlsx
Fallback: Prints errors, returns False
"""

import argparse
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from google.auth.exceptions import RefreshError
from tenacity import retry, stop_after_attempt, wait_exponential
import sys

SHEET_ID = "1Ue3UXj-HYfJMSipy_oJ3wsUEKX9FuJsvZw50b2GrV1o"

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=4, max=20))
def upload_df_to_sheet(df, creds_file='google_credentials.json'):
    print(f"🔍 Looking for {creds_file}")
    if not os.path.exists(creds_file):
        print(f"❌ {creds_file} missing! Download from Google Cloud Console")
        return False
        
    if df.empty:
        print("ℹ️ No data to upload")
        return False
        
    print("🔗 Connecting to Google Sheet...")
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file(creds_file, scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).worksheet('Sheet1')
    print("✅ Google Sheet connected")
        
        # Unique check
        records = sheet.get_all_records()
        existing_emails = {r.get('Email', '') for r in records}
        existing_phones = {r.get('Phone', '') for r in records}
        
        new_rows = []
        for _, row in df.iterrows():
            if row['Email'] not in existing_emails and row['Phone'] not in existing_phones:
                new_rows.append([str(row.get(col, '')) for col in df.columns])
        
        if new_rows:
            sheet.append_rows(new_rows)
            print(f"✅ Uploaded {len(new_rows)} new rows")
            return True
        else:
            print("ℹ️ No new unique rows")
            return True
    return False

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', required=True, help='Excel/CSV file path')
    args = parser.parse_args()
    
    try:
        df = pd.read_excel(args.file) if args.file.endswith('.xlsx') else pd.read_csv(args.file)
        success = upload_df_to_sheet(df)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Using Excel fallback")
        sys.exit(1)
