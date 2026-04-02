#!/usr/bin/env python3
"""
VECTORAX DOCTOR LEAD SCRAPER - PRODUCTION READY FOR RENDER
Selenium + Multi-source + Google Sheets + Fallback Excel + Threading
Fixes 0 leads issue | Anti-captcha | Proxy support | Linux compatible
"""

import os
import time
import logging
import pandas as pd
import json
import random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import re

# Selenium imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

# Google Sheets
import gspread
from google.oauth2.service_account import Credentials
from google.auth.exceptions import RefreshError

# ===== AUTO CREATE DIRECTORIES =====
for dir_name in ['logs', 'data']:
    Path(dir_name).mkdir(exist_ok=True)

# ===== CONFIGURATION =====
CITIES = [
    "Delhi", "Mumbai", "Chennai", "Bangalore"
]

SPECIALTIES = [
    "Cardiologist", "Dermatologist", "Gynecologist", "Neurologist", 
    "Orthopedic Surgeon", "Pediatrician", "General Physician", "Dentist"
]

SHEET_ID = "1Ue3UXj-HYfJMSipy_oJ3wsUEKX9FuJsvZw50b2GrV1o"
OUTPUT_XLSX = "data/doctor_leads_master.xlsx"
OUTPUT_CSV = "data/doctor_leads_master.csv"
OUTPUT_JSON = "data/doctor_leads_master.json"

# Proxies (add your proxies here)
PROXIES = []  # ['socks5://user:pass@ip:port', ...]

THREAD_WORKERS = 2  # Safe for Windows/Render
MAX_RETRIES = 3

ua = UserAgent()

# ===== LOGGING =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('VectoraxScraper')

# ===== REGEX PATTERNS ===== (Updated for India phones)
EMAIL_REGEX = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
PHONE_REGEX = re.compile(r'(\+91|91|0)?[6-9]\d{9}')
FAKE_EMAILS = {'example.com', 'test.com', 'dummy.com', 'sample.com'}

# ===== LOAD MASTER DATA =====
def load_master_excel():
    if Path(OUTPUT_XLSX).exists():
        try:
            df = pd.read_excel(OUTPUT_XLSX)
            logger.info(f"Loaded {len(df)} existing leads")
            return df
        except Exception as e:
            logger.error(f"Excel load error: {e}")
    return pd.DataFrame()

df_master = load_master_excel()

# ===== TELEGRAM (Optional) =====
def send_telegram(msg):
    # Implementation same as before - skipped for brevity, keep print if no token
    print(f"📱 {msg}")

# ===== SELENIUM DRIVER FACTORY =====
def get_driver(proxy=None, headless=True):
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument(f'--user-agent={ua.random}')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    if headless:
        options.add_argument('--headless')
    
    if proxy:
        options.add_argument(f'--proxy-server={proxy}')
    
    # Image disable for speed
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)
    
    service = ChromeDriverManager().install()
    driver = webdriver.Chrome(service=webdriver.chrome.service.Service(service), options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

# ===== DIRECT SITE SCRAPERS =====
# Practo, Justdial, Apollo, Fortis, Kauvery - No Google needed

def scrape_practo(city_slug, specialty_slug, driver):
    """Practo direct scraping"""
    url = f"https://www.practo.com/{city_slug}/search/doctors?results_type=doctor&q={specialty_slug}"
    leads = []
    try:
        driver.get(url)
        time.sleep(random.uniform(5, 8))
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        
        page_source_lower = driver.page_source.lower()
        if any(word in page_source_lower for word in ['captcha', 'verify', 'unusual']):
            logger.warning(f"CAPTCHA on Practo {city_slug}")
            return leads
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        cards = soup.select('a[href*="/doctor/"], .doctor-name-card, .doctor-card, .name-card, [class*="doctor"], h1, h2, h3')
        
        for card in cards[:12]:
            name_elem = card.select_one('.doctor-name, h2, .name, .u-t-m, .ellipsis')
            hospital_elem = card.select_one('.clinic-name, .sub-title')
            link_elem = card.select_one('a[href*="/doctor/"]')
            
            name = name_elem.get_text(strip=True) if name_elem else ''
            hospital = hospital_elem.get_text(strip=True) if hospital_elem else 'Practo Listed Clinic'
            profile_url = link_elem['href'] if link_elem else ''
            if profile_url and not profile_url.startswith('http'):
                profile_url = 'https://www.practo.com' + profile_url
            
            if 'dr' in name.lower():
                leads.append({
                    'name': name,
                    'specialty': specialty_slug.title(),
                    'hospital': hospital,
                    'city': city_slug.title(),
                    'profile_url': profile_url
                })
        
        logger.info(f"Practo {city_slug}: {len(leads)} doctors")
    except Exception as e:
        logger.warning(f"Practo failed {city_slug}: {e}")
    return leads

def scrape_justdial(city_slug, specialty_slug, driver):
    """Justdial direct"""
    url = f"https://www.justdial.com/{city_slug}/{specialty_slug}-doctors/nct-1"
    leads = []
    try:
        driver.get(url)
        time.sleep(6)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        cards = soup.select('.store-details, .jcn, .result-box, .cntanr, .store-name, a[href*="/profile"], [class*="doctor"], h1, h2')
        
        for card in cards[:12]:
            name_elem = card.select_one('h2, .store-name')
            hospital_elem = card.select_one('.catl')
            link_elem = card.select_one('a')
            
            name = name_elem.get_text(strip=True) if name_elem else ''
            hospital = hospital_elem.get_text(strip=True) if hospital_elem else 'Justdial Listed'
            profile_url = link_elem['href'] if link_elem else ''
            if profile_url and not profile_url.startswith('http'):
                profile_url = 'https://www.justdial.com' + profile_url
            
            if name and ('dr' in name.lower() or 'doctor' in name.lower()):
                leads.append({
                    'name': name,
                    'specialty': specialty_slug.title(),
                    'hospital': hospital,
                    'city': city_slug.title(),
                    'profile_url': profile_url
                })
        logger.info(f"Justdial {city_slug}: {len(leads)}")
    except Exception as e:
        logger.warning(f"Justdial failed: {e}")
    return leads

# ===== PAGE SCRAPER WITH SELENIUM =====
@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(multiplier=1, min=2, max=8), retry=retry_if_exception_type((NoSuchElementException,)))
def selenium_scrape_page(url, driver, city, specialty):
    leads = []
    try:
        driver.get(url)
        time.sleep(random.uniform(3, 6))
        
        # Scroll for dynamic content
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        # Captcha check
        page_source = driver.page_source.lower()
        if any(word in page_source for word in ['captcha', 'verify you are human', 'unusual traffic']):
            logger.warning(f"Captcha on {url}")
            return []
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        text = soup.get_text()
        
        emails = [e for e in EMAIL_REGEX.findall(text) if e.split('@')[1] not in FAKE_EMAILS]
        phones = PHONE_REGEX.findall(text)
        
        # Extract name/clinic/address hints
        name_candidates = re.findall(r'(Dr\.[^,;\n]+|Doctor[^,;\n]+|[A-Z][a-z]+ [A-Z][a-z]+ Clinic)', text)[:3]
        address_candidates = re.findall(r'([0-9/]+ [A-Za-z ,.]+(?:St|Rd|Ave|Nagar|Road|Street))', text)[:2]
        
        for email in emails:
            phone = phones[0] if phones else ''
            lead = {
                'Name': name_candidates[0] if name_candidates else '',
                'Email': email,
                'Phone': phone,
                'Specialty': specialty,
                'City': city,
                'Clinic/Hospital': '',
                'Address': address_candidates[0] if address_candidates else '',
                'Website': url,
                'Source': url.split('/')[2].split('.')[0].title(),
                'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            leads.append(lead)
            
    except Exception as e:
        logger.warning(f"Scrape failed {url}: {e}")
    
    return leads

# ===== GOOGLE SHEETS UPLOAD =====
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=20),
    retry=retry_if_exception_type((TimeoutException, RefreshError))
)
def upload_to_google_sheet(df_new):
    print("🔗 Connecting to Google Sheet...")
    
    if not Path('google_credentials.json').exists():
        raise FileNotFoundError("google_credentials.json missing")
    
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = Credentials.from_service_account_file('google_credentials.json', scopes=scope)
    client = gspread.authorize(creds)
    
    sheet = client.open_by_key(SHEET_ID).worksheet('Sheet1')
    print("Google Sheet connected ✅")
    
    # Get existing emails/phones
    existing_emails = set()
    existing_phones = set()
    try:
        records = sheet.get_all_records()
        for row in records:
            if row.get('Email'):
                existing_emails.add(row['Email'])
            if row.get('Phone'):
                existing_phones.add(row['Phone'])
    except:
        pass  # New sheet
    
    # Filter new unique
    new_rows = []
    for _, row in df_new.iterrows():
        if row['Email'] not in existing_emails and row['Phone'] not in existing_phones:
            new_rows.append([row[col] for col in df_new.columns])
    
    if new_rows:
        sheet.append_rows(new_rows)
        print(f"Rows uploaded successfully: {len(new_rows)}")
    else:
        print("No new unique rows to upload")

# ===== CITY PROCESSOR =====
def process_city(city):
    leads = []
    driver = None
    try:
        proxy = random.choice(PROXIES) if PROXIES else None
        driver = get_driver(proxy=proxy, headless=True)
        
        city_slug = city.lower().replace(' ', '-')
        
        for specialty in SPECIALTIES:
            specialty_slug = specialty.lower().replace(' ', '-')
            
            # Direct scraping from all sites
            practo_leads = scrape_practo(city_slug, specialty_slug, driver)
            leads.extend(practo_leads)
            
            time.sleep(random.uniform(8, 12))
            
            justdial_leads = scrape_justdial(city_slug, specialty_slug, driver)
            leads.extend(justdial_leads)
            
            time.sleep(random.uniform(8, 12))
            
            time.sleep(8)  # Skip Apollo, Fortis, Kauvery for now - focus on working sites
            
            logger.info(f"{city}-{specialty}: Practo+Justdial complete")
            
            logger.info(f"{city}-{specialty}: {len(practo_leads + justdial_leads)} total leads")
            time.sleep(random.uniform(10, 15))  # Specialty cooldown
            
    except Exception as e:
        logger.error(f"City {city} failed: {e}")
    finally:
        if driver:
            driver.quit()
    
    return leads

# ===== MAIN =====
def main():
    start_time = time.time()
    print("🚀 Vectorax Doctor Scraper Started")
    send_telegram("🚀 Production Scraper Started")
    logger.info("=== PRODUCTION SCRAPER START ===")
    
    print(f"🔄 Scraping {len(CITIES)} cities x {len(SPECIALTIES)} specialties...")
    
    all_leads = []
    with ThreadPoolExecutor(max_workers=THREAD_WORKERS) as executor:
        futures = [executor.submit(process_city, city) for city in CITIES]
        for i, future in enumerate(futures):
            city_leads = future.result()
            all_leads.extend(city_leads)
            print(f"✅ City {i+1}/{len(CITIES)}: {len(city_leads)} leads")
            logger.info(f"City {i+1} complete: {len(city_leads)} leads")
    
    # ===== PROCESS LEADS =====
        # Convert direct leads to full format
        full_leads = []
        for lead in all_leads:
            full_lead = {
                'Name': lead['name'],
                'Email': '',
                'Phone': '',
                'Specialty': lead['specialty'],
                'City': lead['city'],
                'Clinic/Hospital': lead['hospital'],
                'Address': '',
                'Website': lead['profile_url'],
                'Source': 'Direct Scrape',
                'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            full_leads.append(full_lead)
            
        if full_leads:
            df_new = pd.DataFrame(full_leads)
            df_new.drop_duplicates(subset=['Website'], inplace=True)  # Dedupe by profile
            
            df_all = pd.concat([df_master, df_new], ignore_index=True)
            
            # Save all formats
            df_all.to_excel(OUTPUT_XLSX, index=False)
            df_all.to_csv(OUTPUT_CSV, index=False)
            df_all.to_json(OUTPUT_JSON, orient='records', indent=2)
            
            new_count = len(df_new)
            total_count = len(df_all)
            
            print(f"✅ NEW LEADS: {new_count}")
            print(f"📊 TOTAL LEADS: {total_count}")
            print(f"📁 SAVED: {OUTPUT_XLSX}")
            print(f"📁 SAVED: {OUTPUT_CSV}")
            print(f"📁 SAVED: {OUTPUT_JSON}")
            print(f"🔗 PROFILES COLLECTED: {len(all_leads)}")
            
            # Google Sheets with fallback
            try:
                upload_to_google_sheet(df_new)
            except Exception as e:
                print(f"❌ Google Sheet failed ({e}) - Using Excel fallback")
                logger.error(f"Sheets error: {e}")
            
            send_telegram(f"✅ Done! {new_count} new | Total {total_count}")
        else:
            print("⚠️ No new leads found")
    
    duration = time.time() - start_time
    print(f"⏱️ Execution time: {duration:.1f}s")
    logger.info(f"Completed in {duration:.1f}s")

if __name__ == '__main__':
    main()
