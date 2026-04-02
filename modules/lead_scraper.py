#!/usr/bin/env python3
"""Lead Scraper Module - Integrated for CRM Bot
Refactored from scraper.py + doctor_scraper_pro.py
Render-safe (minimal selenium, API-first)"""

import logging
import re
import asyncio
from typing import List, Dict, Optional
import pandas as pd
from pathlib import Path
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
import aiohttp
from fake_useragent import UserAgent
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger('LeadScraper')

class LeadScraper:
    def __init__(self):
        self.ua = UserAgent()
        self.email_regex = re.compile(r'[a-zA-Z0-9._%+-]+@[a-z]{2,}\.[a-z]{2,}')
        self.phone_regex = re.compile(r'[+]?[1-9]\d{7,14}')
        self.cities = ['Delhi', 'Mumbai', 'Pune', 'Bangalore']
        self.specialties = ['Cardiologist', 'Dentist', 'Neurologist']

    @retry(stop=stop_after_attempt(3))
    async def search_google(self, query: str) -> List[str]:
        """DuckDuckGo proxy for Google search - Render safe"""
        try:
            with DDGS() as ddgs:
                return [r['href'] for r in ddgs.text(query, max_results=10)]
        except:
            return []

    async def scrape_lead(self, url: str) -> Optional[Dict]:
        """Lightweight scraper"""
        try:
            headers = {'User-Agent': self.ua.random}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=30) as resp:
                    html = await resp.text()
            
            soup = BeautifulSoup(html, 'html.parser')
            data = self._extract(soup, url)
            if self.is_valid(data):
                logger.info(f'✅ New lead: {data.get("name")}')
                return data
        except:
            pass
        return None

    def _extract(self, soup: BeautifulSoup, url: str) -> Dict:
        text = soup.get_text()
        data = {
            'Doctor Name': '',
            'Specialty': '',
            'City': '',
            'Phone': '',
            'Email': '',
            'Hospital': '',
            'Source': url
        }
        
        # Name patterns
        patterns = [r'dr[\\s.]+([A-Z][a-z]+ [A-Z][a-z]+)']
        for pat in patterns:
            m = re.search(pat, text, re.I)
            if m:
                data['Doctor Name'] = m.group(1)
                break
        
        # Email
        emails = self.email_regex.findall(text)
        data['Email'] = emails[0] if emails else ''
        
        # Phone
        phones = self.phone_regex.findall(text)
        data['Phone'] = phones[0] if phones else ''
        
        return data

    def is_valid(self, data: Dict) -> bool:
        return bool(data['Doctor Name'] and (data['Email'] or data['Phone']))

    async def scrape_daily(self, limit: int = 50) -> List[Dict]:
        """Daily scrape for new leads"""
        all_leads = []
        for city in self.cities[:2]:  # Limit for Render
            for spec in self.specialties:
                query = f'{spec} doctor {city} contact'
                urls = await self.search_google(query)
                leads = await asyncio.gather(*(self.scrape_lead(url) for url in urls[:5]))
                all_leads.extend([l for l in leads if l])
                if len(all_leads) > limit:
                    break
            if len(all_leads) > limit:
                break
        logger.info(f'Scraped {len(all_leads)} new leads')
        return all_leads

    def append_to_master(self, new_leads: List[Dict]):
        """Append to master Excel"""
        p = Path('data/doctor_leads_master.xlsx')
        df_new = pd.DataFrame(new_leads)
        if p.exists():
            df_old = pd.read_excel(p)
            df = pd.concat([df_old, df_new]).drop_duplicates(subset=['Email', 'Phone'])
        else:
            df = df_new
        df.to_excel(p, index=False)
        logger.info(f'Appended to master: {len(df)} total')

