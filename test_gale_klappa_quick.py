#!/usr/bin/env python3
"""Quick test for Gale Klappa at WEC."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["SEC_EDGAR_USER_AGENT"] = "Ethan Houseworth (ejhouseworthh@gmail.com)"

from sec_edgar_mcp.insider_tools import get_insider_transactions

print("Testing Gale Klappa at WEC...")

try:
    result = get_insider_transactions(
        person_name="Gale Klappa",
        company="WEC",
        start_date="2020-01-01",
        end_date="2025-06-24",
        user_agent="Ethan Houseworth (ejhouseworthh@gmail.com)"
    )
    
    print(f"Found {result['transaction_count']} transactions")
    print(f"Total shares sold: {result['summary']['total_shares_sold']:,.0f}")
    print(f"Total shares bought: {result['summary']['total_shares_bought']:,.0f}")
    
    if result['transactions']:
        print("\nRecent transactions:")
        for trans in result['transactions'][:5]:
            print(f"  {trans['transaction_date']}: {trans['transaction_type']} {trans['shares']:,.0f} shares")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()