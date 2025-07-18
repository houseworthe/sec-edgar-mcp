#!/usr/bin/env python3
"""Simple test to debug filing retrieval."""

import os
os.environ["SEC_EDGAR_USER_AGENT"] = "Ethan Houseworth (ejhouseworthh@gmail.com)"

from secedgar import filings, FilingType
from datetime import date

# Get Form 4 filings for PLOW
print("Getting Form 4 filings for PLOW...")
company_filings = filings(
    cik_lookup="PLOW",
    filing_type=FilingType.FILING_4,
    user_agent="Ethan Houseworth (ejhouseworthh@gmail.com)",
    start_date=date(2022, 1, 1),
    end_date=date(2025, 6, 24)
)

print(f"Filing object: {company_filings}")
print(f"Filing type: {type(company_filings)}")

# Try to get URLs
try:
    urls = company_filings.get_urls()
    print(f"URLs type: {type(urls)}")
    print(f"URLs content: {urls}")
    
    if isinstance(urls, dict):
        for key, value in urls.items():
            print(f"\nKey: {key}")
            print(f"Value type: {type(value)}")
            if isinstance(value, list):
                print(f"Number of URLs: {len(value)}")
                for i, url in enumerate(value[:5]):
                    print(f"  {i+1}. {url}")
            else:
                print(f"Value: {value}")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()