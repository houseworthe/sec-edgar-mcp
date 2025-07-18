#!/usr/bin/env python3
"""Test script to verify cross-company search fix for Gale Klappa."""

import os
import sys
import logging
from datetime import date, timedelta

# Add the package to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sec_edgar_mcp.cross_company_search import get_all_insider_companies, get_current_board_positions
from sec_edgar_mcp.person_cik_resolver import PersonCIKResolver
from sec_edgar_mcp.sec_fulltext_search import SECFullTextSearcher

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Test configuration
USER_AGENT = os.getenv('SEC_EDGAR_USER_AGENT', 'Test Company test@example.com')
TEST_PERSON = "Gale Klappa"
EXPECTED_COMPANIES = ["WEC", "ASB", "BMI"]  # WEC Energy, Associated Banc-Corp, Badger Meter


def test_fulltext_search():
    """Test the new full-text search functionality."""
    print("\n=== Testing Full-Text Search ===")
    
    searcher = SECFullTextSearcher(USER_AGENT)
    
    # Test basic search
    print(f"\nSearching for Form 4s by {TEST_PERSON}...")
    results = searcher.search_form4_by_person(
        person_name=TEST_PERSON,
        start_date=date.today() - timedelta(days=5*365),
        limit=50
    )
    
    print(f"Found {len(results)} Form 4 filings")
    
    # Get unique companies
    companies = searcher.get_companies_for_person(TEST_PERSON)
    print(f"\nFound {len(companies)} unique companies:")
    
    for company in companies[:5]:  # Show first 5
        print(f"  - {company.get('ticker', 'N/A')}: {company.get('company_name')} "
              f"({company.get('filing_count')} filings, "
              f"last: {company.get('last_filing', 'N/A')})")
    
    # Check if we found expected companies
    found_tickers = {c.get('ticker') for c in companies if c.get('ticker')}
    missing = set(EXPECTED_COMPANIES) - found_tickers
    if missing:
        print(f"\nWARNING: Did not find expected companies: {missing}")
    else:
        print(f"\nSUCCESS: Found all expected companies!")
    
    return len(companies) > 0


def test_cross_company_search():
    """Test the enhanced cross-company search."""
    print("\n=== Testing Cross-Company Search ===")
    
    # Test with full-text search (new method)
    print(f"\n1. Testing with full-text search for {TEST_PERSON}...")
    result = get_all_insider_companies(
        person_name=TEST_PERSON,
        include_former=True,
        user_agent=USER_AGENT,
        use_fulltext_search=True
    )
    
    print(f"\nResults from full-text search:")
    print(f"  Total companies: {result['summary']['total_companies']}")
    print(f"  Active positions: {result['summary']['active_positions']}")
    print(f"  Former positions: {result['summary']['former_positions']}")
    print(f"  Search method: {result['search_method']}")
    
    if result['companies']:
        print(f"\nCompanies found:")
        for company in result['companies']:
            print(f"  - {company['ticker']}: {company['company_name']} "
                  f"(Status: {company['position_status']}, "
                  f"Transactions: {company['transaction_summary']['total_transactions']})")
    
    # Check if we found expected companies
    found_tickers = {c['ticker'] for c in result['companies']}
    missing = set(EXPECTED_COMPANIES) - found_tickers
    if missing:
        print(f"\nWARNING: Did not find expected companies: {missing}")
        
        # Try with name variations
        print("\n2. Trying with SEC name format 'KLAPPA GALE E'...")
        result2 = get_all_insider_companies(
            person_name="KLAPPA GALE E",
            include_former=True,
            user_agent=USER_AGENT,
            use_fulltext_search=True
        )
        print(f"  Found {result2['summary']['total_companies']} companies")
    else:
        print(f"\nSUCCESS: Found all expected companies!")
    
    return result['summary']['total_companies'] > 0


def test_cik_resolver():
    """Test the person CIK resolver."""
    print("\n=== Testing CIK Resolver ===")
    
    resolver = PersonCIKResolver(USER_AGENT)
    
    print(f"\nResolving CIK for {TEST_PERSON}...")
    result = resolver.resolve_person_cik(TEST_PERSON)
    
    if result:
        print(f"\nSUCCESS: Resolved CIK")
        print(f"  CIK: {result['cik']}")
        print(f"  Canonical name: {result['name']}")
        print(f"  Name variations: {result['name_variations']}")
        print(f"  Known companies: {result['companies']}")
        print(f"  Confidence: {result['confidence']:.2f}")
    else:
        print(f"\nFAILED: Could not resolve CIK for {TEST_PERSON}")
    
    return result is not None


def test_current_positions():
    """Test getting current board positions."""
    print("\n=== Testing Current Board Positions ===")
    
    result = get_current_board_positions(
        person_name=TEST_PERSON,
        user_agent=USER_AGENT
    )
    
    print(f"\nCurrent positions for {TEST_PERSON}:")
    print(f"  Count: {result['current_positions_count']}")
    
    if result['current_positions']:
        print("\nCurrent positions:")
        for pos in result['current_positions']:
            print(f"  - {pos['ticker']}: {pos['company_name']} "
                  f"(Position: {pos.get('current_position', 'N/A')})")
    
    return result['current_positions_count'] > 0


def main():
    """Run all tests."""
    print(f"Testing cross-company search fixes for: {TEST_PERSON}")
    print(f"Expected to find activity at: {', '.join(EXPECTED_COMPANIES)}")
    print(f"User Agent: {USER_AGENT}")
    
    tests_passed = 0
    tests_total = 4
    
    # Run tests
    if test_fulltext_search():
        tests_passed += 1
    
    if test_cross_company_search():
        tests_passed += 1
    
    if test_cik_resolver():
        tests_passed += 1
    
    if test_current_positions():
        tests_passed += 1
    
    # Summary
    print(f"\n{'='*50}")
    print(f"SUMMARY: {tests_passed}/{tests_total} tests passed")
    
    if tests_passed == tests_total:
        print("✅ All tests passed! The cross-company search is working correctly.")
    else:
        print("❌ Some tests failed. Check the output above for details.")
    
    return tests_passed == tests_total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)