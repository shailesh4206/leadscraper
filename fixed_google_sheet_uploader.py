#!/usr/bin/env python3
"""
🔧 FIXED Google Sheet Uploader - Debugged RetryError
Handles credentials.json + missing files + Windows paths
"""

import argparse
import os
import pandas as pd
import logging
from pathlib import Path
import sys

# Google Sheets
try:
    import gspread
    from google.oauth2.service_account import Credentials
    print("✅ gspread imported")
except ImportError:
    print("❌ pip install gspread google-auth")
    sys.exit(1)

SHEET_ID = "1Ue3UXj-HYfJMSipy_oJ3wsUEKX9FuJsvZw50b2GrV1o"
CREDENTIALS_FILES = ['credentials.json', 'google_credentials.json', 'service_account.json']

def find_credentials():
    """Find credentials file (credentials.json first)"""
    for creds_file in CREDENTIALS_FILES:
        creds_path = Path(creds_file)
        if creds_path.exists():
            print(f"✅ Found: {creds_file}")
            return str(creds_path)
    print("❌ No credentials found. Expected one of:", CREDENTIALS_FILES)
    return None

def test_connection(creds_file):
    """Minimal connection test"""
    print(f"🔗 Testing {creds_file}...")
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    try:
        creds = Credentials.from_service_account_file(creds_file, scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID).sheet1
        print(f"✅ SUCCESS! Sheet: {sheet.title}, Rows: {len(sheet.get_all_values())}")
        return True, sheet
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False, None

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=4, max=20))
def upload_df_to_sheet(df, creds_file, sheet):
    """Upload with detailed logging"""
    print(f"📊 Data shape: {df.shape}")
    
    # Unique check
    records = sheet.get_all_records()
    existing_emails = {r.get('Email', '') for r in records}
    existing_phones = {r.get('Phone', '') for r in records}
    
    print(f"📈 Sheet has {len(records)} rows")
    print(f"🔍 Existing emails: {len(existing_emails)} unique")
    
    new_rows = []
    for idx, row in df.iterrows():
        email = str(row.get('Email', ''))
        phone = str(row.get('Phone', ''))
        if email not in existing_emails and phone not in existing_phones:
            new_rows.append([str(row.get(col, '')) for col in df.columns])
    
    if new_rows:
        sheet.append_rows(new_rows)
        print(f"✅ UPLOADED {len(new_rows)} new rows!")
        return True
    else:
        print("ℹ️ No new unique data")
        return True

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', required=True, help='Excel/CSV file')
    args = parser.parse_args()
    
    # 1. Find credentials
    creds_file = find_credentials()
    if not creds_file:
        print("\n🚀 Get credentials: console.cloud.google.com → IAM → Service Account → JSON Key")
        sys.exit(1)
    
    # 2. Load data
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"❌ File not found: {args.file}")
        sys.exit(1)
    
    try:
        df = pd.read_excel(args.file) if args.file.endswith('.xlsx') else pd.read_csv(args.file)
        print(f"✅ Loaded {len(df)} rows from {args.file}")
    except Exception as e:
        print(f"❌ Load failed: {e}")
        sys.exit(1)
    
    # 3. Test connection
    success, sheet = test_connection(creds_file)
    if not success:
        sys.exit(1)
    
    # 4. Upload
    upload_df_to_sheet(df, creds_file, sheet)
    print("\n🎉 COMPLETE! Check your Google Sheet")

