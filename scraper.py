#!/usr/bin/env python3
"""
Vectorax Doctor Lead Scraper Pro - Main Scraper
Production-ready doctor contact extraction bot
"""

import logging
import re
import time
import pandas as pd
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Optional
from pathlib import Path

# Core scraping
from requests import Session
from bs4 import BeautifulSoup
from googlesearch import search
from fake_useragent import UserAgent
from tenacity import retry, stop_after_attempt, wait_exponential

# Selenium for dynamic content
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Local imports
from config import *
import asyncio
from telegram import Bot

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DoctorLeadExtractor:
    def __init__(self):
        self.session = Session()
        self.ua = UserAgent()
        self.leads = []
        self.email_regex = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        self.phone_regex = re.compile(r'[\+]?[1-9][\d]{0,15}')
        self.doctor_patterns = [
            r'dr\.?\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'doctor\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'([A-Z][a-z]+\s+[A-Z][a-z]+?)(?=\s+(md|mbbs|ms|dm))'
        ]
        
    def generate_search_queries(self) -> List[str]:
        """Generate smart Google search queries"""
        base_queries = [
            f"{SPECIALTY} {CITY} contact",
            f"{SPECIALTY} {CITY} email phone",
            f"{SPECIALTY} {CITY} clinic hospital",
            f"best {SPECIALTY} {CITY} doctor list",
            f"{SPECIALTY} {CITY} practo justdial",
            f"practo {SPECIALTY} {CITY}",
            f"justdial {SPECIALTY} {CITY}"
        ]
        return base_queries

    def init_driver(self) -> webdriver.Chrome:
        """Initialize Selenium Chrome driver"""
        options = Options()
        if HEADLESS_MODE:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument(f'--user-agent={self.ua.random}')
        
        service = webdriver.chrome.service.Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(TIMEOUT)
        return driver

    @retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(multiplier=1, min=4, max=10))
    def scrape_dynamic_page(self, url: str, driver: webdriver.Chrome) -> Optional[Dict]:
        """Scrape JS-heavy dynamic pages"""
        try:
            driver.get(url)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Scroll for lazy loading
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            lead_data = self.extract_lead_data(soup, url)
            
            if lead_data and self.is_valid_lead(lead_data):
                logger.info(f"✅ Dynamic lead found: {lead_data.get('name', 'Unknown')}")
                return lead_data
            return None
            
        except Exception as e:
            logger.warning(f"Selenium failed on {url}: {e}")
            return None

    def scrape_page(self, url: str, use_selenium: bool = False) -> Optional[Dict]:
        """Main scrape dispatcher - BS4 or Selenium based on site"""
        # Use Selenium for dynamic sites
        dynamic_domains = ['practo.com', 'justdial.com']
        use_selenium = use_selenium or any(domain in url for domain in dynamic_domains)
        
        if use_selenium:
            driver = self.init_driver()
            try:
                return self.scrape_dynamic_page(url, driver)
            finally:
                driver.quit()
        
        # Regular BS4 scraping
        headers = {'User-Agent': self.ua.random}
        try:
            resp = self.session.get(url, headers=headers, timeout=TIMEOUT)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            lead_data = self.extract_lead_data(soup, url)
            if lead_data and self.is_valid_lead(lead_data):
                logger.info(f"✅ Found valid lead: {lead_data.get('name', 'Unknown')}")
                return lead_data
            return None
            
        except Exception as e:
            logger.warning(f"Failed to scrape {url}: {e}")
            return None

    @retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(multiplier=1, min=4, max=10))
    def scrape_page(self, url: str) -> Optional[Dict]:
        """Scrape single page for doctor data"""
        headers = {'User-Agent': self.ua.random}
        try:
            resp = self.session.get(url, headers=headers, timeout=TIMEOUT)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            lead_data = self.extract_lead_data(soup, url)
            if lead_data and self.is_valid_lead(lead_data):
                logger.info(f"✅ Found valid lead: {lead_data.get('name', 'Unknown')}")
                return lead_data
            return None
            
        except Exception as e:
            logger.warning(f"Failed to scrape {url}: {e}")
            return None

    def extract_lead_data(self, soup: BeautifulSoup, source_url: str) -> Dict:
        """Extract doctor data using heuristics"""
        data = {
            'name': '',
            'specialty': SPECIALTY,
            'city': CITY,
            'hospital': '',
            'email': '',
            'phone': '',
            'website': '',
            'source_url': source_url
        }
        
        # Extract name
        text = soup.get_text()
        for pattern in self.doctor_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data['name'] = match.group(1).strip().title()
                break
        
        # Extract hospital/clinic (h1, h2, strong tags)
        for tag in soup.find_all(['h1', 'h2', 'strong']):
            candidate = tag.get_text(strip=True)
            if any(word in candidate.lower() for word in ['hospital', 'clinic', 'centre', 'center']):
                data['hospital'] = candidate
                break
        
        # Extract email
        emails = self.email_regex.findall(text)
        for email in emails:
            if self.validate_email(email):
                data['email'] = email.lower()
                break
        
        # Extract phone
        phones = self.phone_regex.findall(text)
        for phone in phones:
            if self.validate_phone(phone):
                data['phone'] = self.format_phone(phone)
                break
        
        # Website
        for link in soup.find_all('a', href=True):
            if 'www' in link['href'] or any(domain in link['href'] for domain in ['practo', 'justdial']):
                data['website'] = urljoin(source_url, link['href'])
                break
        
        return data

    def validate_email(self, email: str) -> bool:
        """Validate email quality"""
        domain = email.split('@')[1] if '@' in email else ''
        if not domain:
            return False
        if domain in INVALID_EMAIL_PATTERNS:
            return False
        if any(domain.endswith(f'@{d}') for d in VALID_EMAIL_DOMAINS):
            return True
        return len(email) > 10

    def validate_phone(self, phone: str) -> bool:
        """Validate phone number"""
        cleaned = re.sub(r'[^\d+]', '', phone)
        return len(cleaned) >= 10

    def format_phone(self, phone: str) -> str:
        """Format phone nicely"""
        cleaned = re.sub(r'[^\d]', '', phone)
        if len(cleaned) == 10:
            return f"+91 {cleaned[:5]} {cleaned[5:]}"
        return phone

    def is_valid_lead(self, data: Dict) -> bool:
        """Must have email OR phone"""
        return bool(data['email'] or data['phone'])

    def deduplicate_leads(self):
        """Remove duplicate leads"""
        if not self.leads:
            return
        
        df = pd.DataFrame(self.leads)
        df.drop_duplicates(subset=['name', 'email', 'phone'], inplace=True)
        self.leads = df.to_dict('records')
        logger.info(f"Deduplicated: {len(self.leads)} unique leads")

    def export_to_excel(self):
        """Save verified leads to Excel"""
        if not self.leads:
            logger.warning("No valid leads to export")
            return
        
        df = pd.DataFrame(self.leads)
        # Reorder and rename columns to exact spec
        df.rename(columns={
            'name': 'Doctor Name',
            'specialty': 'Specialty',
            'city': 'City',
            'hospital': 'Hospital',
            'email': 'Email',
            'phone': 'Phone',
            'website': 'Website',
            'source_url': 'Source URL'
        }, inplace=True)
        
        # Reorder to match requirement
        column_order = ['Doctor Name', 'Specialty', 'City', 'Hospital', 'Email', 'Phone', 'Website', 'Source URL']
        df = df.reindex(columns=[col for col in column_order if col in df.columns])
        
        filepath = Path(OUTPUT_FILE)
        df.to_excel(filepath, index=False)
        logger.info(f"✅ Exported {len(df)} leads to {filepath}")
        return str(filepath.absolute())

    async def send_telegram_notification(self, excel_path: str, lead_count: int):
        """Send Excel file via Telegram bot"""
        if TELEGRAM_TOKEN == "YOUR_BOT_TOKEN_HERE" or TELEGRAM_CHAT_ID == "YOUR_CHAT_ID_HERE":
            logger.info("⚠️  Telegram config missing - skipping notification")
            return
        
        try:
            bot = Bot(token=TELEGRAM_TOKEN)
            message = f"🎉 Vectorax Doctor Scraper Complete!\n\n✅ Found {lead_count} verified {SPECIALTY} leads in {CITY}\n📊 Excel: {Path(excel_path).name}"
            
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
            
            # Send file
            with open(excel_path, 'rb') as f:
                await bot.send_document(
                    chat_id=TELEGRAM_CHAT_ID, 
                    document=f,
                    caption=f"Verified {SPECIALTY} leads from {CITY} - {lead_count} records"
                )
            logger.info("📱 Telegram notification sent successfully!")
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")

async def main():
    logger.info("🚀 Starting Vectorax Doctor Lead Scraper Pro")
    
    extractor = DoctorLeadExtractor()
    queries = extractor.generate_search_queries()
    
    all_urls = []
    for query in queries:
        logger.info(f"🔍 Searching: '{query}'")
        try:
            urls = list(search(query, num_results=SEARCH_LIMIT//len(queries), lang='en'))
            all_urls.extend(urls[:20])  # Top 20 per query
        except Exception as e:
            logger.error(f"Google search failed for '{query}': {e}")
    
    all_urls = list(set(all_urls))[:SEARCH_LIMIT]  # Dedupe & limit
    logger.info(f"📄 Processing {len(all_urls)} URLs")
    
    for i, url in enumerate(all_urls, 1):
        logger.info(f"[{i}/{len(all_urls)}] Scraping: {url}")
        lead = extractor.scrape_page(url)
        if lead:
            extractor.leads.append(lead)
        time.sleep(1.5)  # Polite rate limiting
    
    extractor.deduplicate_leads()
    excel_path = extractor.export_to_excel()
    
    # Send Telegram notification
    if excel_path:
        await extractor.send_telegram_notification(excel_path, len(extractor.leads))
    
    logger.info(f"🎉 Complete! Found {len(extractor.leads)} verified leads")
    logger.info(f"📁 Excel saved: {excel_path}")

if __name__ == "__main__":
    asyncio.run(main())
