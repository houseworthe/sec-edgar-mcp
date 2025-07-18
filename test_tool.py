#!/usr/bin/env python3
"""Test the get_insider_transactions tool directly."""

import os
import sys
import logging

logging.basicConfig(level=logging.DEBUG)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["SEC_EDGAR_USER_AGENT"] = "Ethan Houseworth (ejhouseworthh@gmail.com)"

from sec_edgar_mcp.insider_tools import get_insider_transactions

# Test searching for James L Janik at PLOW
print("Testing get_insider_transactions for James L Janik at PLOW...")
result = get_insider_transactions(
    person_name="James L Janik",
    company="PLOW",
    start_date="2023-01-01",
    end_date="2023-12-31",
    user_agent="Ethan Houseworth (ejhouseworthh@gmail.com)"
)

print(f"\nFound {result['transaction_count']} transactions")
print(f"Summary: {result['summary']}")

if result['transactions']:
    print("\nTransactions:")
    for trans in result['transactions'][:5]:
        print(f"  - {trans['transaction_date']}: {trans['transaction_type']} {trans['shares']} shares")
else:
    print("\nNo transactions found!")
    
# Also try with different name formats
print("\n\nTrying 'Janik James L' (reversed name)...")
result2 = get_insider_transactions(
    person_name="Janik James L",
    company="PLOW", 
    start_date="2023-01-01",
    end_date="2023-12-31",
    user_agent="Ethan Houseworth (ejhouseworthh@gmail.com)"
)

print(f"\nFound {result2['transaction_count']} transactions")