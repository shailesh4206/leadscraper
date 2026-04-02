#!/usr/bin/env python3
"""
Vectorax Global Doctor Lead Scraper Pro v2
Production system: Async + Multi-thread + Global cities + Append Excel
"""

import asyncio
import logging
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from pathlib import Path
from typing import List, Dict
from datetime import datetime

# Existing scrapers
from scraper import DoctorLeadExtractor
from cities.india_cities import INDIA_CITIES
from cities.global_cities import GLOBAL_CITIES  
from cities.specialties import SPECIALTIES
from utils.validator import validate_lead  # Will create
from utils.exporter import append_to_excel  # Will create

# Setup UTF-8 logging (fix Windows emoji issue)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ],
    encoding='utf-8'
)
logger = logging.getLogger(__name__)

async def generate_queries(cities: List[str], specialties: List[str]) -> List[str]:
    """Generate comprehensive search queries"""
    queries = []
    for city in cities:
        for specialty in specialties[:3]:  # Limit per city
            queries.extend([
                f"{specialty} {city} contact email phone",
                f"{specialty} {city} clinic hospital",
                f"best {specialty} doctor {city}",
                f"{specialty} {city} practo justdial"
            ])
    return queries[:500]  # Limit total queries

async def main():
    Path("logs").mkdir(exist_ok=True)
    Path("data").mkdir(exist_ok=True)
    
    logger.info("🚀 Global Doctor Scraper v2 Starting...")
    
    # Extractor instance
    extractor = DoctorLeadExtractor()
    
    # Generate queries from all cities
    cities = INDIA_CITIES + GLOBAL_CITIES[:10]  # Limit global for demo
    queries = await generate_queries(cities, SPECIALTIES)
    
    logger.info(f"Generated {len(queries)} queries from {len(cities)} cities")
    
    # Async search phase (TODO: implement DuckDuckGo)
    urls = await search_urls(queries)
    
    # Multi-thread scraping
    leads = await scrape_batch(urls, extractor, max_workers=10)
    
    # Validate & dedupe
    valid_leads = [validate_lead(lead) for lead in leads if validate_lead(lead)]
    
    # Export
    excel_path = await append_to_excel(valid_leads, "data/doctor_leads_master.xlsx")
    
    logger.info(f"✅ Complete! {len(valid_leads)} valid leads → {excel_path}")

if __name__ == "__main__":
    asyncio.run(main())

