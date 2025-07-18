#!/usr/bin/env python3
"""Check for duplicate filings."""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["SEC_EDGAR_USER_AGENT"] = "Ethan Houseworth (ejhouseworthh@gmail.com)"

from secedgar import filings, FilingType

# Get Form 4 filings for PLOW in 2023
company_filings = filings(
    cik_lookup="PLOW",
    filing_type=FilingType.FILING_4,
    user_agent="Ethan Houseworth (ejhouseworthh@gmail.com)",
    start_date=date(2023, 1, 1),
    end_date=date(2023, 12, 31)
)

urls_dict = company_filings.get_urls()
filing_urls = urls_dict.get('PLOW', [])

print(f"Total URLs: {len(filing_urls)}")

# Check for duplicates
unique_urls = set()
duplicates = []

for url in filing_urls:
    if url in unique_urls:
        duplicates.append(url)
    else:
        unique_urls.add(url)

print(f"Unique URLs: {len(unique_urls)}")
print(f"Duplicates: {len(duplicates)}")

if duplicates:
    print("\nDuplicate URLs:")
    for dup in duplicates[:5]:
        print(f"  {dup}")

# Check accession numbers
accessions = [url.split('/')[-2] for url in filing_urls if '/' in url]
unique_accessions = set(accessions)

print(f"\nTotal accessions: {len(accessions)}")
print(f"Unique accessions: {len(unique_accessions)}")

# Show first few to see pattern
print("\nFirst 10 URLs:")
for i, url in enumerate(filing_urls[:10]):
    print(f"{i+1}. {url}")