"""MCP tools for institutional ownership analysis using 13F/13D/13G filings."""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta
import xml.etree.ElementTree as ET
from secedgar import filings, FilingType
from mcp.server.fastmcp import FastMCP

from .models import InstitutionalHolding, MajorShareholder
from .utils import (
    normalize_cik, normalize_ticker, cached, rate_limited,
    parse_date, parse_datetime, clean_number, validate_cusip
)

logger = logging.getLogger(__name__)


def register_institutional_tools(mcp: FastMCP, user_agent: str):
    """Register all institutional ownership tools with the MCP server."""
    
    @mcp.tool("get_13f_holdings")
    def get_13f_holdings_tool(
        institution: str,
        as_of_date: Optional[str] = None,
        user_agent: str = user_agent
    ) -> Dict[str, Any]:
        """
        Parse institutional investor 13F filings to get holdings.
        
        Parameters:
            institution: Institution name or CIK
            as_of_date: Get holdings as of this date (YYYY-MM-DD)
            user_agent: User agent string required by the SEC
            
        Returns:
            Dictionary containing institutional holdings and portfolio analysis
            
        Example:
            get_13f_holdings("Berkshire Hathaway", "2024-09-30")
        """
        return get_13f_holdings(
            institution=institution,
            as_of_date=as_of_date,
            user_agent=user_agent
        )
    
    @mcp.tool("search_institutional_ownership")
    def search_institutional_ownership_tool(
        stock: str,
        min_shares: Optional[int] = None,
        as_of_date: Optional[str] = None,
        user_agent: str = user_agent
    ) -> Dict[str, Any]:
        """
        Find all institutions holding a specific stock.
        
        Parameters:
            stock: Stock ticker or company name
            min_shares: Minimum shares held to include
            as_of_date: Get ownership as of this date
            user_agent: User agent string required by the SEC
            
        Returns:
            Dictionary containing list of institutional holders
            
        Example:
            search_institutional_ownership("AAPL", min_shares=1000000)
        """
        return search_institutional_ownership(
            stock=stock,
            min_shares=min_shares,
            as_of_date=as_of_date,
            user_agent=user_agent
        )
    
    @mcp.tool("get_ownership_changes")
    def get_ownership_changes_tool(
        institution: str,
        stock: str,
        quarters_back: int = 4,
        user_agent: str = user_agent
    ) -> Dict[str, Any]:
        """
        Track quarter-over-quarter changes in institutional positions.
        
        Parameters:
            institution: Institution name or CIK
            stock: Stock ticker to track
            quarters_back: Number of quarters to analyze
            user_agent: User agent string required by the SEC
            
        Returns:
            Dictionary containing ownership changes over time
            
        Example:
            get_ownership_changes("Vanguard", "MSFT", quarters_back=4)
        """
        return get_ownership_changes(
            institution=institution,
            stock=stock,
            quarters_back=quarters_back,
            user_agent=user_agent
        )
    
    @mcp.tool("get_major_shareholders")
    def get_major_shareholders_tool(
        company: str,
        threshold: float = 5.0,
        user_agent: str = user_agent
    ) -> Dict[str, Any]:
        """
        Parse 13D/13G filings for major shareholders (5%+ ownership).
        
        Parameters:
            company: Company ticker or CIK
            threshold: Ownership percentage threshold (default 5%)
            user_agent: User agent string required by the SEC
            
        Returns:
            Dictionary containing major shareholders and their stakes
            
        Example:
            get_major_shareholders("TSLA", threshold=5.0)
        """
        return get_major_shareholders(
            company=company,
            threshold=threshold,
            user_agent=user_agent
        )


@cached(filing_type='13f')
@rate_limited
def get_13f_holdings(
    institution: str,
    as_of_date: Optional[str] = None,
    user_agent: str = None
) -> Dict[str, Any]:
    """Get institutional holdings from 13F filings."""
    
    holdings = []
    
    try:
        # Get 13F-HR filings for the institution
        inst_filings = filings(
            cik_lookup=institution,
            filing_type=FilingType.FILING_13FHR,
            user_agent=user_agent,
            count=4  # Get last 4 quarters
        )
        
        # For simplified implementation, return structure
        # Full implementation would parse the 13F XML/HTML tables
        
        return {
            "institution": institution,
            "as_of_date": as_of_date or date.today().isoformat(),
            "holdings": [],
            "portfolio_value": 0,
            "position_count": 0,
            "message": "13F parsing implementation pending"
        }
        
    except Exception as e:
        logger.error(f"Error getting 13F holdings: {e}")
        return {
            "error": str(e),
            "institution": institution
        }


def search_institutional_ownership(
    stock: str,
    min_shares: Optional[int] = None,
    as_of_date: Optional[str] = None,
    user_agent: str = None
) -> Dict[str, Any]:
    """Search for institutional owners of a stock."""
    
    # This would require:
    # 1. Getting all recent 13F filings
    # 2. Parsing each to find holdings of the specific stock
    # 3. Aggregating results
    
    return {
        "stock": stock,
        "as_of_date": as_of_date or date.today().isoformat(),
        "institutional_holders": [],
        "total_institutional_shares": 0,
        "message": "Cross-institutional search implementation pending"
    }


def get_ownership_changes(
    institution: str,
    stock: str,
    quarters_back: int = 4,
    user_agent: str = None
) -> Dict[str, Any]:
    """Track ownership changes over time."""
    
    return {
        "institution": institution,
        "stock": stock,
        "quarters_analyzed": quarters_back,
        "changes": [],
        "message": "Ownership tracking implementation pending"
    }


@cached(filing_type='13d')
@rate_limited
def get_major_shareholders(
    company: str,
    threshold: float = 5.0,
    user_agent: str = None
) -> Dict[str, Any]:
    """Get major shareholders from 13D/13G filings."""
    
    major_holders = []
    
    try:
        # Get 13D filings
        filings_13d = filings(
            cik_lookup=company,
            filing_type=FilingType.FILING_SC13D,
            user_agent=user_agent,
            count=20
        )
        
        # Get 13G filings
        filings_13g = filings(
            cik_lookup=company,
            filing_type=FilingType.FILING_SC13G,
            user_agent=user_agent,
            count=20
        )
        
        # For simplified implementation, return structure
        
        return {
            "company": company,
            "threshold": threshold,
            "major_shareholders": [],
            "total_reported_ownership": 0,
            "message": "13D/13G parsing implementation pending"
        }
        
    except Exception as e:
        logger.error(f"Error getting major shareholders: {e}")
        return {
            "error": str(e),
            "company": company
        }