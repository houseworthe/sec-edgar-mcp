#!/usr/bin/env python3
"""Test with detailed debugging."""

import os
import sys
import logging
import requests

logging.basicConfig(level=logging.DEBUG)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["SEC_EDGAR_USER_AGENT"] = "Ethan Houseworth (ejhouseworthh@gmail.com)"

from sec_edgar_mcp.form4_parser import Form4Parser
from secedgar import filings, FilingType
from datetime import date

# Get one specific filing we know has Janik
parser = Form4Parser("Ethan Houseworth (ejhouseworthh@gmail.com)")

# Direct test of known good filing
print("=== Direct test of known filing ===")
xml_url = "https://www.sec.gov/Archives/edgar/data/1287213/000156761923003206/doc1.xml"
xml_content = parser.fetch_filing_content(xml_url)
print(f"Fetched {len(xml_content)} chars")

# Check if name is in content
if "Janik" in xml_content:
    print("✓ 'Janik' found in XML content")
if "James L Janik" in xml_content:
    print("✓ 'James L Janik' found in XML content")  
if "janik james l" in xml_content.lower():
    print("✓ 'janik james l' found in XML content (case insensitive)")

# Parse it
transactions = parser.parse_form4_xml(xml_content, "test-accession")
print(f"\nParsed {len(transactions)} transactions")
for t in transactions:
    print(f"  {t.insider_name}: {t.transaction_type.name} {t.shares} shares")

# Now test through the filings API
print("\n\n=== Test through filings API ===")
company_filings = filings(
    cik_lookup="PLOW",
    filing_type=FilingType.FILING_4,
    user_agent="Ethan Houseworth (ejhouseworthh@gmail.com)",
    start_date=date(2023, 2, 1),
    end_date=date(2023, 2, 28)
)

urls_dict = company_filings.get_urls()
filing_urls = urls_dict.get('PLOW', [])
print(f"Found {len(filing_urls)} filings in Feb 2023")

# Check first few
for i, url in enumerate(filing_urls[:5]):
    print(f"\nFiling {i+1}: {url}")
    
    # Get index page
    index_content = parser.fetch_filing_content(url)
    
    # Find XML filename
    import re
    xml_match = re.search(r'<FILENAME>([^<]+\\.xml)', index_content)
    if xml_match:
        xml_filename = xml_match.group(1)
        base_url = url.rsplit('/', 1)[0]
        xml_url = f"{base_url}/{xml_filename}"
        print(f"  XML URL: {xml_url}")
        
        # Get XML
        xml_content = parser.fetch_filing_content(xml_url)
        
        # Quick name check
        if "Janik" in xml_content:
            print(f"  ✓ Contains 'Janik'")
            
            # Extract name properly
            name_match = re.search(r'<rptOwnerName>([^<]+)</rptOwnerName>', xml_content)
            if name_match:
                print(f"  Name in XML: '{name_match.group(1)}'")
                
            # Parse
            trans = parser.parse_form4_xml(xml_content, f"acc-{i}")
            print(f"  Parsed {len(trans)} transactions")
            for t in trans:
                print(f"    {t.insider_name}: {t.transaction_type.name} {t.shares}")