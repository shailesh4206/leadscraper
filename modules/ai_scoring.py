#!/usr/bin/env python3
"""AI Lead Scoring - Hot/Warm/Cold"""

import pandas as pd
import logging

logger = logging.getLogger('AIScorer')

def score_leads(df: pd.DataFrame) -> pd.DataFrame:
    """Rule-based scoring"""
    df = df.copy()
    
    # Default
    df['Lead Score'] = 'Cold'
    
    # Hot: Hospital + phone + email
    df.loc[
(df['Hospital'].str.contains('hospital|medical center', case=False, na=False)) &
        df['Phone'].notna() & (df['Phone'].str.len() > 5) &
        df['Email'].notna(),
        'Lead Score'
    ] = 'Hot'
    
    # Warm: Clinic + phone OR email
    df.loc[
        ((df['Hospital'].str.contains('clinic', case=False, na=False)) | 
         df['Hospital'].str.contains('centre', case=False, na=False)) &
        (df['Phone'].notna() | df['Email'].notna()),
        'Lead Score'
    ] = 'Warm'
    
    logger.info(f'Scoring: {df["Lead Score"].value_counts().to_dict() }')
    return df

