#!/usr/bin/env python3
"""
🏥 DOCTOR LEADS EXCEL → STRUCTURED CRM TRANSFORMER
Auto-updates your doctor_leads_master.xlsx with exact column mapping
Production-ready - One command execution
"""

import pandas as pd
import numpy as np
import re
from pathlib import Path
import argparse
from datetime import datetime, timedelta

CITY_MAP = {
    'mumbai': 'Mumbai', 'delhi': 'Delhi', 'bangalore': 'Bengaluru', 
    'pune': 'Pune', 'hyderabad': 'Hyderabad', 'chennai': 'Chennai',
    'kolkata': 'Kolkata', 'ahmedabad': 'Ahmedabad', 'jaipur': 'Jaipur'
}

STATE_MAP = {
    'mumbai': 'Maharashtra', 'pune': 'Maharashtra', 'ahmedabad': 'Gujarat',
    'delhi': 'Delhi', 'bangalore': 'Karnataka', 'hyderabad': 'Telangana',
    'chennai': 'Tamil Nadu', 'kolkata': 'West Bengal', 'jaipur': 'Rajasthan'
}

def clean_phone(phone):
    """Convert float → string + standardize India format"""
    if pd.isna(phone) or phone == 'nan':
        return ''
    
    phone_str = str(phone).strip()
    phone_str = re.sub(r'[^\d+]', '', phone_str)  # Keep digits + +
    
    if len(phone_str) == 10:
        return f"+91 {phone_str[:5]} {phone_str[5:]}"
    elif len(phone_str) in [11, 12] and phone_str.startswith('91'):
        return f"+91 {phone_str[2:7]} {phone_str[7:]}"
    elif len(phone_str) >= 10:
        return f"+91 {phone_str[-10:]}"
    return phone_str

def extract_doctor_name(url):
    """Extract from profile URL"""
    try:
        if 'practo' in url.lower():
            # practo.com/hyderabad/dr-john-doe
            parts = Path(url).name.split('-')
            if len(parts) >= 2 and parts[0].startswith('dr'):
                return 'Dr. ' + ' '.join(parts[1:]).replace('-', ' ').title()
        elif 'justdial' in url.lower():
            parts = Path(url).name.split('-')
            for part in parts:
                if 'dr' in part.lower():
                    return part.replace('-', ' ').title()
    except:
        pass
    return "Dr. Specialist"

def transform_dataset(input_path):
    """Main transformer"""
    print(f"📂 Loading {input_path}")
    
    # Load Excel
    df = pd.read_excel(input_path)
    print(f"📊 Original: {len(df)} rows, columns: {list(df.columns)}")
    
    # Clean data
    df = df.replace({np.nan: '', None: ''})
    
    # Extract names
    df['Actual Doctor Name'] = df['Website'].apply(extract_doctor_name)
    fallback_mask = df['Actual Doctor Name'].str.contains('Dr. Specialist', na=False)
    df.loc[fallback_mask, 'Actual Doctor Name'] = df.loc[fallback_mask, 'Doctor Name']
    
    # Transform columns
    df['Search Keyword'] = df['Doctor Name']  # Original search
    df['Category'] = df['Specialty']
    df['Phone Number'] = df['Phone Number'].apply(clean_phone)
    df['Email Address'] = df['Email Address'].str.lower()
    
    # Location standardization
    df['City'] = df['City'].astype(str).str.strip().str.lower()
    df['City'] = df['City'].map(CITY_MAP).fillna(df['City'].str.title())
    df['State'] = df['City'].map(STATE_MAP).fillna('')
    df['Country'] = 'India'
    
    # Links
    df['Clinic / Website Source'] = df['Hospital / Clinic Name'].fillna(df['Website'])
    df['Doctor Profile Link'] = df['Website']
    df['Google Maps Link'] = ''
    df['Source URL'] = df['Source URL']
    
    # CRM fields
    df['Lead Status'] = '🆕 New Lead'
    df['Contacted'] = 'No'
    df['Interested'] = 'Pending'
    df['Follow-up Date'] = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')
    df['Assigned To'] = ''
    df['Notes'] = ''
    
    # Keep timestamp
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
    
    # Deduplicate (phone + email priority)
    dup_cols = ['Phone Number', 'Email Address']
    before_dup = len(df)
    df = df.drop_duplicates(subset=dup_cols, keep='first')
    print(f"✅ Deduplicated: {before_dup - len(df)} removed")
    
    # Final CRM structure
    crm_columns = [
        'Actual Doctor Name', 'Search Keyword', 'Category', 'Phone Number', 
        'Email Address', 'City', 'District', 'State', 'Country', 
        'Clinic / Website Source', 'Doctor Profile Link', 'Google Maps Link',
        'Source URL', 'Lead Status', 'Contacted', 'Interested', 
        'Follow-up Date', 'Assigned To', 'Notes', 'Timestamp'
    ]
    
    df_crm = df[crm_columns].copy()
    
    return df_crm

def main():
    parser = argparse.ArgumentParser(description="Transform Doctor Leads → CRM Excel")
    parser.add_argument('--input', '-i', default='data/doctor_leads_master.xlsx', 
                       help='Input Excel file')
    parser.add_argument('--output', '-o', default='data/doctor_crm_final.xlsx',
                       help='Output CRM Excel file')
    args = parser.parse_args()
    
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ {args.input} not found!")
        print("Generate first: python perfect_doctor_scraper.py")
        return
    
    # Transform
    df_crm = transform_dataset(args.input)
    
    # Save
    output_path = Path(args.output)
    df_crm.to_excel(output_path, index=False)
    print(f"\n💾 SAVED: {output_path}")
    print(f"✅ CRM-Ready: {len(df_crm)} leads")
    
    # Preview
    preview_cols = ['Actual Doctor Name', 'Phone Number', 'Email Address', 'City', 'Lead Status']
    print("\n📋 PREVIEW:")
    print(df_crm[preview_cols].head())
    
    print(f"\n🚀 Upload now:")
    print(f"python fixed_google_sheet_uploader_v2.py --file {args.output}")

if __name__ == '__main__':
    main()

