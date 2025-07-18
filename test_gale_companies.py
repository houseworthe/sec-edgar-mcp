#!/usr/bin/env python3
"""Test Gale Klappa across different companies."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["SEC_EDGAR_USER_AGENT"] = "Ethan Houseworth (ejhouseworthh@gmail.com)"

from sec_edgar_mcp.insider_tools import get_insider_transactions

def check_company(ticker, company_name):
    """Check if Gale Klappa has transactions at a company."""
    print(f"\nChecking {ticker} ({company_name})...")
    
    try:
        result = get_insider_transactions(
            person_name="Gale Klappa", 
            company=ticker,
            start_date="2020-01-01",
            end_date="2025-06-24",
            user_agent="Ethan Houseworth (ejhouseworthh@gmail.com)"
        )
        
        if result['transaction_count'] > 0:
            print(f"  ✅ Found {result['transaction_count']} transactions")
            print(f"  📈 Shares sold: {result['summary']['total_shares_sold']:,.0f}")
            print(f"  📉 Shares bought: {result['summary']['total_shares_bought']:,.0f}")
            return True
        else:
            print(f"  ❌ No transactions found")
            return False
            
    except Exception as e:
        print(f"  ⚠ Error: {e}")
        return False

# Test companies where Gale Klappa might be an insider
companies = [
    ("WEC", "WEC Energy Group"),
    ("SO", "Southern Company"), 
    ("NEE", "NextEra Energy"),
    ("EXC", "Exelon Corp")
]

print("TESTING GALE KLAPPA ACROSS COMPANIES")
print("=" * 50)

found_companies = []

for ticker, name in companies:
    if check_company(ticker, name):
        found_companies.append((ticker, name))

print(f"\n📋 SUMMARY:")
print(f"Companies where Gale Klappa is an insider: {len(found_companies)}")

for ticker, name in found_companies:
    print(f"  • {name} ({ticker})")