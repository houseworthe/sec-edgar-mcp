#!/usr/bin/env python3
"""Comprehensive test suite for all SEC EDGAR MCP tools."""

import os
import sys
import logging

# Setup
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["SEC_EDGAR_USER_AGENT"] = "Ethan Houseworth (ejhouseworthh@gmail.com)"

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_insider_tools():
    """Test all insider trading tools."""
    print("=" * 60)
    print("TESTING INSIDER TRADING TOOLS")
    print("=" * 60)
    
    from sec_edgar_mcp.insider_tools import (
        get_insider_transactions, get_recent_insider_activity, 
        analyze_insider_patterns, get_form4_details
    )
    
    user_agent = "Ethan Houseworth (ejhouseworthh@gmail.com)"
    
    # Test 1: get_insider_transactions
    print("\n1. Testing get_insider_transactions...")
    try:
        result = get_insider_transactions(
            person_name="James L Janik",
            company="PLOW",
            start_date="2023-01-01",
            end_date="2023-12-31",
            user_agent=user_agent
        )
        print(f"   ✓ Found {result['transaction_count']} transactions")
        print(f"   ✓ Net shares: {result['summary']['net_shares']:,.0f}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 2: get_recent_insider_activity
    print("\n2. Testing get_recent_insider_activity...")
    try:
        result = get_recent_insider_activity(
            company="PLOW",
            days_back=365,
            user_agent=user_agent
        )
        print(f"   ✓ Found {result['transaction_count']} transactions by {result['insider_count']} insiders")
        if result['insiders']:
            top_insider = list(result['insiders'].keys())[0]
            print(f"   ✓ Top insider: {top_insider}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 3: analyze_insider_patterns
    print("\n3. Testing analyze_insider_patterns...")
    try:
        result = analyze_insider_patterns(
            company="PLOW",
            time_period="1Y",
            user_agent=user_agent
        )
        print(f"   ✓ Buy/sell ratio: {result.get('buy_sell_ratio', 'N/A')}")
        print(f"   ✓ Sentiment: {result.get('net_insider_sentiment', 'N/A')}")
        print(f"   ✓ Active insiders: {len(result.get('most_active_insiders', []))}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 4: get_form4_details
    print("\n4. Testing get_form4_details...")
    try:
        # Use a known accession number from our previous tests
        result = get_form4_details(
            accession_number="0001567619-23-003206",
            user_agent=user_agent
        )
        print(f"   ✓ Insider count: {result.get('insider_count', 0)}")
        print(f"   ✓ Transaction count: {result.get('transaction_count', 0)}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

def test_institutional_tools():
    """Test institutional holdings tools."""
    print("\n" + "=" * 60)
    print("TESTING INSTITUTIONAL HOLDINGS TOOLS")
    print("=" * 60)
    
    try:
        from sec_edgar_mcp.institutional_tools import (
            get_13f_holdings, get_institutional_ownership,
            search_13d_13g_filings, analyze_ownership_changes
        )
        
        user_agent = "Ethan Houseworth (ejhouseworthh@gmail.com)"
        
        # Test 1: get_13f_holdings
        print("\n1. Testing get_13f_holdings...")
        try:
            result = get_13f_holdings(
                cik="0001067983",  # Berkshire Hathaway
                quarter="2024Q1",
                user_agent=user_agent
            )
            print(f"   ✓ Holdings found: {len(result.get('holdings', []))}")
            print(f"   ✓ Total value: ${result.get('total_value', 0):,.0f}")
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        # Test 2: get_institutional_ownership
        print("\n2. Testing get_institutional_ownership...")
        try:
            result = get_institutional_ownership(
                ticker="AAPL",
                quarter="2024Q1",
                user_agent=user_agent
            )
            print(f"   ✓ Institution count: {len(result.get('institutions', []))}")
            print(f"   ✓ Total shares held: {result.get('total_shares', 0):,.0f}")
        except Exception as e:
            print(f"   ✗ Error: {e}")
            
    except ImportError as e:
        print(f"   ⚠ Institutional tools not available: {e}")

def test_financial_tools():
    """Test financial segment revenue tools."""
    print("\n" + "=" * 60)
    print("TESTING FINANCIAL SEGMENT TOOLS")
    print("=" * 60)
    
    try:
        from sec_edgar_mcp.financial_parser import (
            get_segment_revenue, get_product_revenue,
            analyze_revenue_trends, get_geographic_revenue
        )
        
        user_agent = "Ethan Houseworth (ejhouseworthh@gmail.com)"
        
        # Test 1: get_segment_revenue
        print("\n1. Testing get_segment_revenue...")
        try:
            result = get_segment_revenue(
                ticker="AAPL",
                period="annual",
                years=2,
                user_agent=user_agent
            )
            print(f"   ✓ Segments found: {len(result.get('segments', []))}")
            print(f"   ✓ Years covered: {len(result.get('years', []))}")
        except Exception as e:
            print(f"   ✗ Error: {e}")
            
    except ImportError as e:
        print(f"   ⚠ Financial tools not available: {e}")

def test_analysis_tools():
    """Test analysis and unified search tools."""
    print("\n" + "=" * 60)
    print("TESTING ANALYSIS & UNIFIED SEARCH TOOLS")
    print("=" * 60)
    
    try:
        from sec_edgar_mcp.analysis_tools import (
            bulk_entity_analysis, compare_companies,
            track_ownership_changes
        )
        from sec_edgar_mcp.unified_search import unified_search
        
        user_agent = "Ethan Houseworth (ejhouseworthh@gmail.com)"
        
        # Test 1: bulk_entity_analysis
        print("\n1. Testing bulk_entity_analysis...")
        try:
            result = bulk_entity_analysis(
                entities=["AAPL", "MSFT"],
                analysis_type="ownership",
                user_agent=user_agent
            )
            print(f"   ✓ Entities analyzed: {len(result.get('entities', []))}")
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        # Test 2: unified_search
        print("\n2. Testing unified_search...")
        try:
            result = unified_search(
                query="Apple iPhone revenue",
                search_type="product_revenue",
                user_agent=user_agent
            )
            print(f"   ✓ Search completed")
            print(f"   ✓ Results: {len(result.get('results', []))}")
        except Exception as e:
            print(f"   ✗ Error: {e}")
            
    except ImportError as e:
        print(f"   ⚠ Analysis tools not available: {e}")

def test_mcp_server():
    """Test the MCP server integration."""
    print("\n" + "=" * 60)
    print("TESTING MCP SERVER INTEGRATION")
    print("=" * 60)
    
    try:
        # Try importing the server
        from sec_edgar_mcp.server import mcp
        print("   ✓ MCP server imports successfully")
        
        # Check if tools are registered
        tools = mcp._tools if hasattr(mcp, '_tools') else {}
        print(f"   ✓ Registered tools: {len(tools)}")
        
        # List some key tools
        key_tools = [
            'get_insider_transactions',
            'get_recent_insider_activity', 
            'analyze_insider_patterns'
        ]
        
        for tool in key_tools:
            if tool in tools:
                print(f"   ✓ Tool '{tool}' registered")
            else:
                print(f"   ✗ Tool '{tool}' missing")
                
    except Exception as e:
        print(f"   ✗ MCP server error: {e}")

if __name__ == "__main__":
    print("SEC EDGAR MCP COMPREHENSIVE TEST SUITE")
    print("=" * 60)
    
    # Run all tests
    test_insider_tools()
    test_institutional_tools()
    test_financial_tools()
    test_analysis_tools()
    test_mcp_server()
    
    print("\n" + "=" * 60)
    print("TEST SUITE COMPLETE")
    print("=" * 60)