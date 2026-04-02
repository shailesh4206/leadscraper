#!/usr/bin/env python3
"""
🏥 DOCTOR LEADS → CRM DATA CLEANER
Transform search keywords → Real doctor names + CRM structure
Production-ready dataset formatter
"""

import pandas as pd
import re
import numpy as np
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import argparse
from datetime import datetime, timedelta

def extract_doctor_name_from_url(url):
    """Extract real doctor name from profile URL"""
    try:
        parsed = urlparse(url)
        path = parsed.path.lower()
        
        # Practo: /hyderabad/dr-name-specialty
        if 'practo' in parsed.netloc:
            parts = path.split('/')
            if len(parts) >= 3 and parts[2].startswith('dr-'):
                return parts[2].replace('dr-', 'Dr. ').replace('-', ' ').title()
        
        # Justdial: /pune/dr-name-id
        if 'justdial' in parsed.netloc:
            parts = path.split('/')
            for part in parts:
                if part.startswith('dr-'):
                    return part.replace('dr-', 'Dr. ').replace('-', ' ').title()
        
        # Generic: extract from query/title
        qs = parse_qs(parsed.query)
        for key in qs:
            val = qs[key][0].lower()
            if 'dr' in val:
                return val.replace('dr-', 'Dr. ').title()
                
    except:
        pass
    return "Doctor"

def standardize_city_state(city):
    """Standardize city names"""
    city_map = {
        'mumbai': 'Mumbai', 'delhi': 'Delhi', 'bangalore': 'Bengaluru',
        'pune': 'Pune', 'hyderabad': 'Hyderabad', 'chennai': 'Chennai',
        'kolkata': 'Kolkata', 'ahmedabad': 'Ahmedabad'
    }
    return city_map.get(city.lower(), city.title())

def clean_phone(phone):
    """Convert float phone to string + clean"""
    if pd.isna(phone):
        return ''
    
    phone_str = str(phone).strip()
    # Remove float artifacts
    phone_str = re.sub(r'^nan$', '', phone_str)
    phone_str = re.sub(r'[^\d+]', '', phone_str)
    
    if len(phone_str) == 10:
        return f"+91 {phone_str[:5]} {phone_str[5:]}"
    elif len(phone_str) >= 10:
        return f"+91 {phone_str[-10:]}"
    return phone_str

def transform_to_crm(df):
    """Transform to CRM structure"""
    print(f"🔄 Processing {len(df)} raw leads...")
    
    # Extract real names from URL
    df['Contact Name'] = df['Website'].apply(extract_doctor_name_from_url)
    
    # Fallback to Doctor Name if generic
    mask = df['Contact Name'].str.contains('Doctor', case=False, na=False)
    df.loc[mask, 'Contact Name'] = df.loc[mask, 'Doctor Name']
    
    # Clean core fields
    df['Category'] = df['Specialty']
    df['Phone Number'] = df['Phone Number'].apply(clean_phone)
    df['Email Address'] = df['Email Address'].astype(str).str.lower()
    df['City'] = df['City'].apply(standardize_city_state)
    df['State'] = df['City'].str.split().str[0] + ' State'  # Simple standardization
    df['Country'] = 'India'
    df['Clinic / Source Website'] = df['Hospital / Clinic Name'].fillna(df['Website'])
    df['Profile Link'] = df['Website']
    
    # CRM columns
    df['Lead Status'] = '🆕 New Lead'
    df['Contacted'] = 'No'
    df['Interested'] = 'Pending'
    df['Follow-up Date'] = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')
    df['Assigned To'] = 'Team'
    df['Notes'] = ''
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
    
    # Deduplicate
    dup_cols = ['Phone Number', 'Email Address']
    before = len(df)
    df = df.drop_duplicates(subset=dup_cols, keep='first')
    print(f"✅ Deduped: {before-len(df)} duplicates removed")
    
    # Select CRM columns
    crm_columns = [
        'Contact Name', 'Category', 'Phone Number', 'Email Address', 
        'City', 'State', 'Country', 'Clinic / Source Website', 
        'Profile Link', 'Lead Status', 'Contacted', 'Interested', 
        'Follow-up Date', 'Assigned To', 'Notes', 'Timestamp'
    ]
    
    df_crm = df[crm_columns].copy()
    
    # Clean NaN
    df_crm = df_crm.replace({np.nan: '', None: ''})
    
    print(f"✅ CRM-Ready: {len(df_crm)} leads")
    return df_crm

def main():
    parser = argparse.ArgumentParser(description="Clean Doctor Leads → CRM Format")
    parser.add_argument('input_file', nargs='?', default='data/doctor_leads_master.xlsx')
    parser.add_argument('--output', '-o', default='data/doctor_crm_cleaned.xlsx')
    args = parser.parse_args()
    
    # Load
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"❌ Input not found: {args.input_file}")
        print("Generate first: python perfect_doctor_scraper.py")
        return
    
    if args.input_file.endswith('.xlsx'):
        df = pd.read_excel(args.input_file)
    else:
        df = pd.read_csv(args.input_file)
    
    # Transform
    df_crm = transform_to_crm(df)
    
    # Save
    output_path = Path(args.output)
    df_crm.to_excel(output_path, index=False)
    print(f"💾 Saved: {output_path}")
    
    # Preview
    print("\n📋 FIRST 3 LEADS:")
    print(df_crm[['Contact Name', 'Phone Number', 'Email Address', 'Lead Status']].head(3))
    
    print(f"\n🎉 CLEANED DATA READY!")
    print(f"Upload: python healthcare_crm_automation.py --file {args.output}")

if __name__ == '__main__':
    main()

