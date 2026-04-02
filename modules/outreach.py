#!/usr/bin/env python3
"""Outreach Module - Email Placeholder (WhatsApp risky)"""
import logging
from pathlib import Path
import pandas as pd

logger = logging.getLogger('Outreach')

def send_intro_emails(df: pd.DataFrame, dry_run=True):
    """Send intro emails (Twilio/SendGrid for prod)"""
    hot_leads = df[df['Lead Score'] == 'Hot']
    
    for _, row in hot_leads.iterrows():
        if row['Email']:
            if dry_run:
                logger.info(f'[DRY] Email to {row["Email"]}: Hi Dr {row["Doctor Name"]}, intro...')
            else:
                # TODO: Integrate SMTP/SendGrid
                pass
        logger.info(f'Outreach logged: {len(hot_leads)} Hot leads')
    
    df['WhatsApp Status'] = 'Pending'  # Placeholder
    df['Last Message Sent'] = pd.Timestamp.now().strftime('%Y-%m-%d')
    return df

