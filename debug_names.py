#!/usr/bin/env python3
"""Debug script to see all insider names in Form 4 filings."""

import os
import sys
import logging

logging.basicConfig(level=logging.INFO)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["SEC_EDGAR_USER_AGENT"] = "Ethan Houseworth (ejhouseworthh@gmail.com)"

from secedgar import filings, FilingType
from datetime import date
from sec_edgar_mcp.form4_parser import Form4Parser

# Get Form 4 filings for PLOW
company_filings = filings(
    cik_lookup="PLOW",
    filing_type=FilingType.FILING_4,
    user_agent="Ethan Houseworth (ejhouseworthh@gmail.com)",
    start_date=date(2023, 1, 1),
    end_date=date(2023, 12, 31)
)

urls_dict = company_filings.get_urls()
filing_urls = urls_dict.get('PLOW', [])

print(f"Found {len(filing_urls)} Form 4 filings for PLOW in 2023")

parser = Form4Parser("Ethan Houseworth (ejhouseworthh@gmail.com)")
insider_names = set()

# Check first 20 filings
for i, filing_url in enumerate(filing_urls[:20]):
    try:
        # Get index content
        index_content = parser.fetch_filing_content(filing_url)
        if index_content and '<FILENAME>' in index_content:
            # Find XML filename
            import re
            xml_match = re.search(r'<FILENAME>([^<]+\.xml)', index_content)
            if xml_match:
                xml_filename = xml_match.group(1)
                base_url = filing_url.rsplit('/', 1)[0]
                xml_url = f"{base_url}/{xml_filename}"
                
                # Fetch XML
                xml_content = parser.fetch_filing_content(xml_url)
                if xml_content:
                    # Just extract the name quickly
                    name_match = re.search(r'<rptOwnerName>([^<]+)</rptOwnerName>', xml_content)
                    if name_match:
                        name = name_match.group(1)
                        insider_names.add(name)
                        
                        # Check for James/Janik
                        if 'janik' in name.lower() or 'james' in name.lower():
                            print(f"FOUND MATCH: {name} in filing {i+1}: {filing_url}")
                            print(f"  XML URL: {xml_url}")
    except Exception as e:
        print(f"Error processing filing {i+1}: {e}")

print(f"\nUnique insider names found:")
for name in sorted(insider_names):
    print(f"  - {name}")