#!/usr/bin/env python3
"""Test a specific Form 4 filing."""

import os
import sys
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["SEC_EDGAR_USER_AGENT"] = "Ethan Houseworth (ejhouseworthh@gmail.com)"

from sec_edgar_mcp.form4_parser import Form4Parser

# Test with a specific filing URL from 2023 - one we know has Janik
test_url = "https://www.sec.gov/Archives/edgar/data/1287213/000156761923003206/0001567619-23-003206.txt"

# This is the index page, we need to find the XML document
print(f"Fetching index page: {test_url}")

headers = {'User-Agent': 'Ethan Houseworth (ejhouseworthh@gmail.com)'}
response = requests.get(test_url, headers=headers)

print(f"Response status: {response.status_code}")
print(f"Content length: {len(response.text)}")

# Look for Form 4 XML references in the content
if "James L Janik" in response.text:
    print("✓ Found James L Janik in filing")
else:
    print("✗ James L Janik not found in filing")

# Look for XML document references
lines = response.text.split('\n')
for line in lines:
    if 'FILENAME' in line and '.xml' in line.lower():
        print(f"Found XML file: {line.strip()}")
    if 'doc4.xml' in line.lower() or 'ownership' in line.lower():
        print(f"Found ownership doc: {line.strip()}")

# Try to get the primary document
if '<FILENAME>primary_doc.xml' in response.text:
    print("\nFound primary_doc.xml reference")
    
# Construct proper XML URL
base_url = test_url.rsplit('/', 1)[0]
# Try doc1.xml based on what we found
xml_url = f"{base_url}/doc1.xml"
print(f"\nTrying XML URL: {xml_url}")

xml_response = requests.get(xml_url, headers=headers)
print(f"XML Response status: {xml_response.status_code}")

if xml_response.status_code == 200:
    print(f"XML Content length: {len(xml_response.text)}")
    print("\nFirst 500 chars of XML:")
    print(xml_response.text[:500])
    
    # Test parsing
    parser = Form4Parser("Ethan Houseworth (ejhouseworthh@gmail.com)")
    transactions = parser.parse_form4_xml(xml_response.text, "0001567619-23-003213")
    print(f"\nParsed {len(transactions)} transactions")
    
    for trans in transactions:
        print(f"  - {trans.insider_name}: {trans.transaction_type.name} {trans.shares} shares on {trans.transaction_date}")