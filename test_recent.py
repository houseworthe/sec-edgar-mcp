#!/usr/bin/env python3
"""Test recent insider activity with longer period."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["SEC_EDGAR_USER_AGENT"] = "Ethan Houseworth (ejhouseworthh@gmail.com)"

from sec_edgar_mcp.insider_tools import get_recent_insider_activity

# Test with 365 days to catch recent activity
result = get_recent_insider_activity(
    company="PLOW",
    days_back=365,
    user_agent="Ethan Houseworth (ejhouseworthh@gmail.com)"
)

print(f"Found {result['transaction_count']} transactions by {result['insider_count']} insiders")

if result['insiders']:
    print("\nTop insiders by activity:")
    for name, data in list(result['insiders'].items())[:5]:
        print(f"  {name}: {len(data['transactions'])} transactions, net {data['net_shares']:,.0f} shares")

if result['recent_transactions']:
    print(f"\nMost recent transactions:")
    for trans in result['recent_transactions'][:5]:
        print(f"  {trans['transaction_date']}: {trans['insider_name']} {trans['transaction_type']} {trans['shares']:,.0f} shares")