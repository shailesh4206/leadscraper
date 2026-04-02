#!/usr/bin/env python3
"""
VECTORAX DOCTOR LEAD SCRAPER - FIXED DATA FETCH ERROR
✅ BeautifulSoup import moved to TOP | Indentation fixed | Production ready
"""

import os
import time
import logging
import pandas as pd
from threading import Thread
from queue import Queue
import requests
from fake_useragent import UserAgent
import re
from bs4 import BeautifulSoup  # ✅ FIXED: Import at TOP

# -------------------------
# CONFIGURATION - BLACKBOX READY
# -------------------------

# 1️⃣ Demo Mode OFF → Full production scraping
DEMO_MODE = False

# 2️⃣ Output files ✅ Auto-create data/ dir
os.makedirs("data", exist_ok=True)
OUTPUT_XLSX = "data/doctor_leads_master.xlsx"
OUTPUT_CSV = "data/doctor_leads_master.csv"
OUTPUT_JSON = "data/doctor_leads_master.json"

# 3️⃣ Cities (India + Global)
CITIES = [
    "Mumbai","Delhi","Bangalore","Chennai","Hyderabad",
    "Kolkata","Pune","Ahmedabad","Jaipur","Lucknow",
    "Chandigarh","Bhopal","Nagpur",
    # Global examples
    "London","New York","Dubai","Singapore","Sydney"
]

# 4️⃣ Specialties
SPECIALTIES = ["Cardiologist","Dermatologist","Gynecologist","Neurologist",
               "Orthopedic","Pediatrician","General Physician"]

# 5️⃣ Threads
THREADS = 8

# 6️⃣ Logging
if not os.path.exists("logs"):
    os.makedirs("logs")
logging.basicConfig(filename="logs/scraper.log",
                    level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# 7️⃣ Data Storage
if os.path.exists(OUTPUT_XLSX):
    df_master = pd.read_excel(OUTPUT_XLSX)
else:
    df_master = pd.DataFrame(columns=[
        "Name","Email","Phone","Specialty","City","Clinic/Hospital",
        "Address","Website","Source","Timestamp"
    ])

# -------------------------
# FUNCTIONS
# -------------------------

ua = UserAgent()

def fetch_doctor_data(city, specialty):
    """Fetch doctor leads from multiple sources ✅ FIXED INDENTATION"""
    leads = []
    try:
        # ✅ Google search + BeautifulSoup parsing
        query = f'{specialty} doctor {city} "contact" OR email OR phone OR clinic -inurl:(login signin)'
        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        headers = {"User-Agent": ua.random}
        
        r = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')  # ✅ Proper indentation
        
        # Extract real leads from search results
        for g in soup.find_all('div', class_='g')[:5]:  # Top 5 results
            title = g.find('h3')
            link = g.find('a', href=True)
            if title and link:
                # Quick page scrape for contacts
                try:
                    page_r = requests.get(link['href'], headers=headers, timeout=8)
                    page_soup = BeautifulSoup(page_r.text, 'html.parser')
                    text = page_soup.get_text().lower()
                    
                    # ✅ Real email/phone extraction
                    emails = re.findall(r'[\w\.-]+@[\w\.-]+', text)
                    phones = re.findall(r'[\+]?[6-9]\d{9}', text)
                    
                    for email in emails[:2]:
                        if '@gmail.com' not in email and '@yahoo' not in email:
                            leads.append({
                                "Name": title.get_text()[:50],
                                "Email": email,
                                "Phone": phones[0] if phones else "",
                                "Specialty": specialty,
                                "City": city,
                                "Clinic/Hospital": "Google Search",
                                "Address": "",
                                "Website": link['href'],
                                "Source": "Enterprise Scraper ✅",
                                "Timestamp": pd.Timestamp.now()
                            })
                except:
                    continue
        print(f"✅ {city}-{specialty}: {len(leads)} leads found")
    except Exception as e:
        logging.error(f"Error fetching {specialty} in {city}: {e}")
    return leads

def worker(queue, results):
    while not queue.empty():
        city, specialty = queue.get()
        leads = fetch_doctor_data(city, specialty)
        results.extend(leads)
        queue.task_done()
        print(f"✅ Processed {city} - {specialty}: {len(leads)} leads")

# -------------------------
# MAIN EXECUTION
# -------------------------

print("🚀 VECTORAX DOCTOR SCRAPER STARTED")
start_time = time.time()
logging.info("🚀 VECTORAX DOCTOR SCRAPER STARTED")

queue = Queue()
results = []

# Fill queue with city-specialty combos
print(f"Loading {len(CITIES)} cities x {len(SPECIALTIES)} specialties")
for city in CITIES:
    for spec in SPECIALTIES:
        queue.put((city, spec))

threads = []
for i in range(THREADS):
    t = Thread(target=worker, args=(queue, results))
    t.daemon = True
    t.start()
    threads.append(t)

# Wait all threads
queue.join()

# -------------------------
# DEDUPLICATE & SAVE
# -------------------------
print(f"Processing {len(results)} total leads...")
df_new = pd.DataFrame(results)

if len(df_new) > 0:
    # Deduplicate new data
    df_new.drop_duplicates(subset=["Email", "Phone"], inplace=True)
    
    # Append to master
    df_combined = pd.concat([df_master, df_new], ignore_index=True)
    df_combined.drop_duplicates(subset=["Email", "Phone"], keep='last', inplace=True)
    
    # Save all formats
    df_combined.to_excel(OUTPUT_XLSX, index=False)
    df_combined.to_csv(OUTPUT_CSV, index=False)
    df_combined.to_json(OUTPUT_JSON, orient="records", indent=4)
    
    new_count = len(df_new)
    total_count = len(df_combined)
    
    logging.info(f"✅ Added {new_count} new leads. Total: {total_count}")
    print(f"✅ Added {new_count} new leads!")
    print(f"📊 Total leads in database: {total_count}")
    print(f"📁 Files saved:")
    print(f"   - {OUTPUT_XLSX}")
    print(f"   - {OUTPUT_CSV}")
    print(f"   - {OUTPUT_JSON}")

logging.info(f"No new leads found")
print("⚠️ No new leads found this run")

end_time = time.time()
duration = end_time - start_time
logging.info(f"⏱️ Duration: {duration:.1f}s | New Leads: {len(df_new)} | Total: {total_count}")
print(f"⏱️ Duration: {duration:.1f} seconds")
print("🏆 VECTORAX SCRAPER COMPLETE!")

if __name__ == "__main__":
    # Auto-run
    exec(open(__file__).read())

