#!/usr/bin/env python3
"""Test the specific boss questions about Gale Klappa."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["SEC_EDGAR_USER_AGENT"] = "Ethan Houseworth (ejhouseworthh@gmail.com)"

from sec_edgar_mcp.insider_tools import get_insider_transactions
from datetime import date, timedelta

def test_gale_klappa_wec_sales():
    """Question 1: How many shares of WEC has Gale Klappa sold over the last 5 years?"""
    print("BOSS QUESTION 1: Gale Klappa WEC Sales (Last 5 Years)")
    print("=" * 60)
    
    # Calculate 5 years back
    end_date = date.today()
    start_date = end_date - timedelta(days=5*365)
    
    try:
        result = get_insider_transactions(
            person_name="Gale Klappa",
            company="WEC",
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            transaction_types=["SALE"],  # Only sales
            user_agent="Ethan Houseworth (ejhouseworthh@gmail.com)"
        )
        
        print(f"Search Period: {start_date} to {end_date}")
        print(f"Found {result['transaction_count']} sale transactions")
        
        total_shares_sold = result['summary']['total_shares_sold']
        total_value_sold = result['summary']['total_value_sold']
        
        print(f"\n📊 ANSWER:")
        print(f"   Total Shares Sold: {total_shares_sold:,.0f}")
        print(f"   Total Value Sold: ${total_value_sold:,.0f}")
        
        if result['transactions']:
            print(f"\n💰 Recent Sales:")
            for trans in result['transactions'][:10]:  # Show first 10
                price = trans.get('price_per_share', 0)
                value = trans.get('total_value', 0)
                print(f"   {trans['transaction_date']}: {trans['shares']:,.0f} shares @ ${price:.2f} = ${value:,.0f}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_gale_klappa_companies():
    """Question 2: How many companies is Gale Klappa an insider for?"""
    print("\n\nBOSS QUESTION 2: Gale Klappa's Companies")
    print("=" * 60)
    
    # Since we don't have cross-company search, let's try a few major utilities
    # where Gale Klappa might be an insider (he's known in the utility sector)
    
    test_companies = [
        ("WEC", "Wisconsin Energy Corp"),
        ("WEC Energy Group", "WEC"),  # Try alternate name
        ("SO", "Southern Company"),
        ("NEE", "NextEra Energy"),
        ("EXC", "Exelon Corp"),
        ("D", "Dominion Energy"),
        ("AEP", "American Electric Power")
    ]
    
    companies_found = []
    
    print("🔍 Searching for Gale Klappa across utility companies...")
    
    for ticker, company_name in test_companies:
        try:
            print(f"\nChecking {ticker} ({company_name})...")
            
            # Search last 3 years for any activity
            result = get_insider_transactions(
                person_name="Gale Klappa",
                company=ticker,
                start_date="2021-01-01",
                end_date=date.today().isoformat(),
                user_agent="Ethan Houseworth (ejhouseworthh@gmail.com)"
            )
            
            if result['transaction_count'] > 0:
                companies_found.append({
                    'ticker': ticker,
                    'company_name': company_name,
                    'transactions': result['transaction_count'],
                    'latest_date': result['summary']['date_range']['last'] if result['summary']['date_range'] else 'N/A'
                })
                print(f"   ✅ Found {result['transaction_count']} transactions")
            else:
                print(f"   ❌ No transactions found")
                
        except Exception as e:
            print(f"   ⚠ Error checking {ticker}: {e}")
    
    print(f"\n📋 ANSWER:")
    print(f"   Companies where Gale Klappa is an insider: {len(companies_found)}")
    
    if companies_found:
        print(f"\n🏢 Company Details:")
        for company in companies_found:
            print(f"   • {company['company_name']} ({company['ticker']})")
            print(f"     - {company['transactions']} transactions")
            print(f"     - Latest: {company['latest_date']}")
    else:
        print("   No companies found with insider activity")
        print("   (Note: This searches a limited set of utility companies)")
    
    return companies_found

if __name__ == "__main__":
    print("TESTING BOSS QUESTIONS FOR GALE KLAPPA")
    print("=" * 80)
    
    # Test both questions
    sales_result = test_gale_klappa_wec_sales()
    companies_result = test_gale_klappa_companies()
    
    print("\n" + "=" * 80)
    print("SUMMARY FOR BOSS")
    print("=" * 80)
    
    if sales_result:
        print(f"1. WEC Sales (5 years): {sales_result['summary']['total_shares_sold']:,.0f} shares")
    else:
        print("1. WEC Sales: Could not retrieve data")
    
    if companies_result:
        print(f"2. Companies as insider: {len(companies_result)}")
        for company in companies_result:
            print(f"   - {company['company_name']} ({company['ticker']})")
    else:
        print("2. Companies as insider: None found in search")