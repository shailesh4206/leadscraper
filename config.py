#!/usr/bin/env python3
"""
Vectorax Doctor Lead Scraper Pro - Configuration
"""

# Scraping Parameters
CITY = "Pune"  # City to search doctors for
SPECIALTY = "Cardiologist"  # Medical specialty
SEARCH_LIMIT = 10  # Max Google search results to process (small for demo)

# Telegram Integration (Get from @BotFather)
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', "YOUR_BOT_TOKEN_HERE")  # Replace with your bot token

TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', "YOUR_CHAT_ID_HERE")  # Your chat ID


# Scraping Settings
USER_AGENTS_FILE = "user_agents.txt"  # Optional: custom user agents
HEADLESS_MODE = True  # Set False to see browser
TIMEOUT = 30  # Page timeout seconds
MAX_RETRIES = 3  # Retry failed requests

# Data Validation
VALID_EMAIL_DOMAINS = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']
INVALID_EMAIL_PATTERNS = ['example.com', 'test.com', 'dummy.com']

# Output file
OUTPUT_FILE = "vectorax_verified_doctor_leads.xlsx"

print(f"Config loaded: Searching {SEARCH_LIMIT} {SPECIALTY} doctors in {CITY}")

