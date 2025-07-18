#!/usr/bin/env python3
"""Test script for Form 4 parser debugging."""

import sys
import os
import logging

# Set up logging to see debug messages
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set environment variables
os.environ["SEC_EDGAR_USER_AGENT"] = "Ethan Houseworth (ejhouseworthh@gmail.com)"

from sec_edgar_mcp.insider_tools import get_insider_transactions

# Test with known parameters
print("Testing Form 4 parser for James L Janik at Douglas Dynamics (PLOW)")
print("=" * 80)

result = get_insider_transactions(
    person_name="James L Janik",
    company="PLOW",
    start_date="2022-01-01",
    user_agent="Ethan Houseworth (ejhouseworthh@gmail.com)"
)

print(f"\nResults:")
print(f"Insider: {result['insider_name']}")
print(f"Company: {result['company']}")
print(f"Date range: {result['date_range']['start']} to {result['date_range']['end']}")
print(f"Transaction count: {result['transaction_count']}")

if result['transaction_count'] > 0:
    print("\nRecent transactions:")
    for trans in result['transactions'][:5]:
        print(f"  - {trans['transaction_date']}: {trans['transaction_type']} "
              f"{trans['shares']:,.0f} shares at ${trans['price_per_share']:.2f}")
        print(f"    Total value: ${trans['total_value']:,.2f}")
        print(f"    Shares after: {trans['shares_owned_after']:,.0f}")
else:
    print("\nNo transactions found - this indicates the parser is still not working correctly")

if 'summary' in result:
    print(f"\nSummary:")
    print(f"  Total shares bought: {result['summary']['total_shares_bought']:,.0f}")
    print(f"  Total shares sold: {result['summary']['total_shares_sold']:,.0f}")
    print(f"  Net shares: {result['summary']['net_shares']:,.0f}")