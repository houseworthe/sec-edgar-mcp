#!/usr/bin/env python3
"""Test only the tools that actually exist."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["SEC_EDGAR_USER_AGENT"] = "Ethan Houseworth (ejhouseworthh@gmail.com)"

def test_existing_tools():
    """Test tools that are actually implemented."""
    print("TESTING EXISTING TOOLS")
    print("=" * 50)
    
    user_agent = "Ethan Houseworth (ejhouseworthh@gmail.com)"
    
    # 1. Test insider tools (we know these work)
    print("\n1. Insider Tools:")
    try:
        from sec_edgar_mcp.insider_tools import get_insider_transactions
        result = get_insider_transactions(
            person_name="James L Janik",
            company="PLOW", 
            start_date="2023-01-01",
            end_date="2023-12-31",
            user_agent=user_agent
        )
        print(f"   ✓ get_insider_transactions: {result['transaction_count']} transactions")
    except Exception as e:
        print(f"   ✗ get_insider_transactions: {e}")
    
    # 2. Test institutional tools
    print("\n2. Institutional Tools:")
    try:
        from sec_edgar_mcp.institutional_tools import get_13f_holdings
        result = get_13f_holdings(
            institution="0001067983",  # Berkshire
            as_of_date="2024-03-31",
            user_agent=user_agent
        )
        print(f"   ✓ get_13f_holdings: {result.get('total_holdings', 0)} holdings")
    except Exception as e:
        print(f"   ✗ get_13f_holdings: {e}")
    
    # 3. Test financial tools 
    print("\n3. Financial Tools:")
    try:
        from sec_edgar_mcp.financial_parser import get_segment_revenue
        result = get_segment_revenue(
            company="AAPL",
            period="annual",
            years=1,
            user_agent=user_agent
        )
        print(f"   ✓ get_segment_revenue: {len(result.get('segments', []))} segments")
    except Exception as e:
        print(f"   ✗ get_segment_revenue: {e}")
    
    # 4. Test unified search
    print("\n4. Unified Search:")
    try:
        from sec_edgar_mcp.unified_search import unified_search
        result = unified_search(
            query="Apple revenue",
            search_type="general",
            user_agent=user_agent
        )
        print(f"   ✓ unified_search: {len(result.get('results', []))} results")
    except Exception as e:
        print(f"   ✗ unified_search: {e}")
    
    # 5. Check server tool registration
    print("\n5. MCP Server Integration:")
    try:
        from sec_edgar_mcp.server import mcp
        
        # Check if the server has tools attribute
        if hasattr(mcp, '_tools'):
            tools = mcp._tools
            print(f"   ✓ Server has {len(tools)} registered tools")
            
            # List first few tools
            tool_names = list(tools.keys())[:5]
            for name in tool_names:
                print(f"     - {name}")
        else:
            print("   ⚠ Cannot access _tools attribute")
            
    except Exception as e:
        print(f"   ✗ Server integration: {e}")

if __name__ == "__main__":
    test_existing_tools()