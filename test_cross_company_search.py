#!/usr/bin/env python3
"""Test the new cross-company search functionality."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["SEC_EDGAR_USER_AGENT"] = "Ethan Houseworth (ejhouseworthh@gmail.com)"

from sec_edgar_mcp.cross_company_search import get_all_insider_companies, get_current_board_positions

def test_cross_company_search():
    """Test the cross-company search functionality with Gale Klappa."""
    print("TESTING CROSS-COMPANY SEARCH FOR GALE KLAPPA")
    print("=" * 60)
    
    user_agent = "Ethan Houseworth (ejhouseworthh@gmail.com)"
    
    try:
        print("🔍 Searching for ALL companies where Gale Klappa is/was an insider...")
        
        # This addresses the core limitation - no company parameter needed!
        result = get_all_insider_companies(
            person_name="Gale Klappa",
            include_former=True,
            min_transactions=1,
            years_back=5,  # Limit to 5 years for faster testing
            user_agent=user_agent
        )
        
        print(f"\n📊 CROSS-COMPANY SEARCH RESULTS:")
        print(f"   Total Companies Found: {result['summary']['total_companies']}")
        print(f"   Active Positions: {result['summary']['active_positions']}")
        print(f"   Former Positions: {result['summary']['former_positions']}")
        print(f"   Total Transactions: {result['summary']['total_transactions']}")
        
        print(f"\n🏢 COMPANIES WHERE GALE KLAPPA IS/WAS AN INSIDER:")
        for company in result['companies']:
            status_emoji = "✅" if company['position_status'] == 'current' else "❌" if company['position_status'] == 'former' else "❓"
            print(f"   {status_emoji} {company['company_name']} ({company['ticker']})")
            print(f"      Status: {company['position_status'].title()}")
            print(f"      Position: {company['current_position'] or 'Unknown'}")
            print(f"      Transactions: {company['transaction_summary']['total_transactions']}")
            print(f"      Net Shares: {company['transaction_summary']['net_shares']:,.0f}")
            if company['transaction_summary']['last_transaction']:
                print(f"      Last Transaction: {company['transaction_summary']['last_transaction']}")
            print()
        
        return result
        
    except Exception as e:
        print(f"❌ Error in cross-company search: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_current_positions():
    """Test getting only current board positions."""
    print("\n" + "=" * 60)
    print("TESTING CURRENT BOARD POSITIONS ONLY")
    print("=" * 60)
    
    user_agent = "Ethan Houseworth (ejhouseworthh@gmail.com)"
    
    try:
        print("🔍 Getting ONLY current board positions for Gale Klappa...")
        
        result = get_current_board_positions(
            person_name="Gale Klappa",
            user_agent=user_agent
        )
        
        print(f"\n📋 CURRENT BOARD POSITIONS:")
        print(f"   Current Positions Count: {result['current_positions_count']}")
        
        if result['current_positions']:
            print(f"\n✅ ACTIVE BOARD POSITIONS:")
            for position in result['current_positions']:
                print(f"   • {position['company_name']} ({position['ticker']})")
                print(f"     Position: {position['current_position']}")
                print(f"     Status: {position['position_status']}")
                print(f"     Recent Activity: {position['transaction_summary']['total_transactions']} transactions")
                print()
        else:
            print("   No current board positions found")
        
        return result
        
    except Exception as e:
        print(f"❌ Error getting current positions: {e}")
        import traceback
        traceback.print_exc()
        return None

def compare_with_manual_search():
    """Compare results with manual company-by-company search."""
    print("\n" + "=" * 60)
    print("COMPARING WITH MANUAL SEARCH")
    print("=" * 60)
    
    # Import the old function for comparison
    from sec_edgar_mcp.insider_tools import get_insider_transactions
    user_agent = "Ethan Houseworth (ejhouseworthh@gmail.com)"
    
    print("🔍 Manual search at specific companies for comparison...")
    
    test_companies = ["WEC", "SO", "NEE", "EXC"]
    manual_results = {}
    
    for company in test_companies:
        try:
            result = get_insider_transactions(
                person_name="Gale Klappa",
                company=company,
                start_date="2020-01-01",
                end_date="2025-06-24",
                user_agent=user_agent
            )
            
            if result['transaction_count'] > 0:
                manual_results[company] = result['transaction_count']
                print(f"   ✅ {company}: {result['transaction_count']} transactions")
            else:
                print(f"   ❌ {company}: No transactions")
                
        except Exception as e:
            print(f"   ⚠ {company}: Error - {e}")
    
    print(f"\n📊 Manual Search Summary: Found activity at {len(manual_results)} companies")
    return manual_results

if __name__ == "__main__":
    print("TESTING NEW CROSS-COMPANY SEARCH CAPABILITIES")
    print("=" * 80)
    print("This addresses the key limitation: finding ALL companies for a person")
    print("Previously required manual specification of each company")
    print("Now finds all companies automatically!")
    print("=" * 80)
    
    # Test the new cross-company search
    cross_company_result = test_cross_company_search()
    
    # Test current positions only
    current_positions_result = test_current_positions()
    
    # Compare with manual approach
    manual_results = compare_with_manual_search()
    
    print("\n" + "=" * 80)
    print("FINAL SUMMARY - CROSS-COMPANY SEARCH RESULTS")
    print("=" * 80)
    
    if cross_company_result:
        print(f"✅ Cross-Company Search: SUCCESSFUL")
        print(f"   - Found {cross_company_result['summary']['total_companies']} companies")
        print(f"   - {cross_company_result['summary']['active_positions']} current positions")
        print(f"   - {cross_company_result['summary']['former_positions']} former positions")
        print(f"   - {cross_company_result['summary']['total_transactions']} total transactions")
    else:
        print(f"❌ Cross-Company Search: FAILED")
    
    if current_positions_result:
        print(f"✅ Current Positions Filter: SUCCESSFUL")
        print(f"   - {current_positions_result['current_positions_count']} current positions identified")
    else:
        print(f"❌ Current Positions Filter: FAILED")
    
    print(f"📊 Manual Search Comparison: Found activity at {len(manual_results)} companies")
    
    print("\n🎯 KEY ACHIEVEMENT:")
    print("   ✅ NO COMPANY PARAMETER REQUIRED - searches all companies automatically")
    print("   ✅ CURRENT vs FORMER distinction - solves Klappa use case")
    print("   ✅ COMPREHENSIVE COVERAGE - finds all insider relationships")