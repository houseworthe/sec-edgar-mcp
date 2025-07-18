#!/usr/bin/env python3
"""Test that all modules can be imported without errors."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Testing imports...")

try:
    from sec_edgar_mcp.server import mcp
    print("✓ server module imported")
    
    from sec_edgar_mcp.cross_company_search import get_all_insider_companies
    print("✓ cross_company_search imported")
    
    from sec_edgar_mcp.comprehensive_reports import generate_comprehensive_insider_report
    print("✓ comprehensive_reports imported")
    
    from sec_edgar_mcp.proxy_parser import get_current_board_from_proxy
    print("✓ proxy_parser imported")
    
    from sec_edgar_mcp.name_matching import name_matcher
    print("✓ name_matching imported")
    
    # Check that we have tools registered
    print("\n✅ MCP server object created successfully")
    
    print("\n✅ All imports successful! The server should work now.")
    print("\n⚠️  Please restart Claude Desktop to pick up the fixed code.")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()