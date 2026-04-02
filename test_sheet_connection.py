#!/usr/bin/env python3
"""
Minimal Google Sheets connection test
Run: python test_sheet_connection.py
"""

import os
try:
    import gspread
    from google.oauth2.service_account import Credentials
    print("✅ gspread imported")
except ImportError:
    print("❌ Install: pip install gspread google-auth")
    exit(1)

SHEET_ID = "1Ue3UXj-HYfJMSipy_oJ3wsUEKX9FuJsvZw50b2GrV1o"

print("🔍 Checking files...")
print(f"Excel exists: {'✅' if os.path.exists('data/doctor_leads_master.xlsx') else '❌'}")
print(f"Credentials exists: {'✅' if os.path.exists('google_credentials.json') else '❌ MISSING ← Create this'}")

if not os.path.exists('google_credentials.json'):
    print("\n🚀 CREATE CREDENTIALS (5 min):")
    print("1. https://console.cloud.google.com → New Project 'Vectorax'")
    print("2. Enable 'Google Sheets API' + 'Google Drive API'")
    print("3. IAM → Service Accounts → Create → JSON Key → google_credentials.json")
    print("4. Share sheet → Add service@project.iam → Editor")
    exit(0)

print("\n🔗 Testing connection...")
try:
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file('google_credentials.json', scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).sheet1
    print("✅ CONNECTION SUCCESS!")
    print(f"📊 Sheet name: {sheet.title}")
    print(f"📈 Rows: {len(sheet.get_all_values())}")
    print("\n🎉 Ready! Run: python google_sheet_uploader.py --file data/doctor_leads_master.xlsx")
except Exception as e:
    print(f"❌ Error: {e}")

