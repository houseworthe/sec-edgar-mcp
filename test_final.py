#!/usr/bin/env python3
"""Final test of James L Janik transactions."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["SEC_EDGAR_USER_AGENT"] = "Ethan Houseworth (ejhouseworthh@gmail.com)"

from sec_edgar_mcp.insider_tools import get_insider_transactions

# Test for full 2-year period to catch May 2023 purchase
print("Getting James L Janik's transactions at PLOW (2022-2024)...")
result = get_insider_transactions(
    person_name="James L Janik",
    company="PLOW",
    start_date="2022-01-01", 
    end_date="2024-06-24",
    user_agent="Ethan Houseworth (ejhouseworthh@gmail.com)"
)

print(f"\nFound {result['transaction_count']} transactions")
print(f"\nSummary:")
print(f"  Total shares bought: {result['summary']['total_shares_bought']:,.0f}")
print(f"  Total shares sold: {result['summary']['total_shares_sold']:,.0f}")
print(f"  Net shares: {result['summary']['net_shares']:,.0f}")
print(f"  Date range: {result['summary']['date_range']['first']} to {result['summary']['date_range']['last']}")

if result['transactions']:
    print(f"\nAll transactions:")
    for trans in result['transactions']:
        print(f"  {trans['transaction_date']}: {trans['transaction_type']} {trans['shares']:,.0f} shares @ ${trans.get('price_per_share', 0):.2f}")
        if trans.get('shares_after_transaction'):
            print(f"    Holdings after: {trans['shares_after_transaction']:,.0f} shares")

# Calculate current holdings estimate
if result['transactions'] and result['transactions'][0].get('shares_after_transaction'):
    print(f"\n✓ Most recent holdings: {result['transactions'][0]['shares_after_transaction']:,.0f} shares")