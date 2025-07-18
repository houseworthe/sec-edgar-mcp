"""MCP tools for parsing financial segment and revenue data from SEC filings."""

import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from secedgar import filings, FilingType
from mcp.server.fastmcp import FastMCP
from bs4 import BeautifulSoup

from .models import RevenueSegment, GeographicRevenue, ProductRevenueTrend
from .utils import (
    cached, rate_limited, parse_date, clean_number,
    calculate_percentage_change
)

logger = logging.getLogger(__name__)


def register_financial_tools(mcp: FastMCP, user_agent: str):
    """Register all financial parsing tools with the MCP server."""
    
    @mcp.tool("get_product_revenue")
    def get_product_revenue_tool(
        company: str,
        product_name: str,
        start_year: int,
        end_year: Optional[int] = None,
        user_agent: str = user_agent
    ) -> Dict[str, Any]:
        """
        Extract revenue data for specific products/segments from 10-K/10-Q filings.
        
        Parameters:
            company: Company ticker or CIK
            product_name: Name of product/segment to search for
            start_year: Starting year for analysis
            end_year: Ending year (defaults to current year)
            user_agent: User agent string required by the SEC
            
        Returns:
            Dictionary containing product revenue trends over time
            
        Example:
            get_product_revenue("AAPL", "iPhone", 2020, 2024)
        """
        return get_product_revenue(
            company=company,
            product_name=product_name,
            start_year=start_year,
            end_year=end_year,
            user_agent=user_agent
        )
    
    @mcp.tool("get_geographic_revenue")
    def get_geographic_revenue_tool(
        company: str,
        year: int,
        quarter: Optional[int] = None,
        user_agent: str = user_agent
    ) -> Dict[str, Any]:
        """
        Parse geographic revenue splits from filings.
        
        Parameters:
            company: Company ticker or CIK
            year: Year to analyze
            quarter: Optional quarter (1-4), if None gets annual data
            user_agent: User agent string required by the SEC
            
        Returns:
            Dictionary containing revenue breakdown by geography
            
        Example:
            get_geographic_revenue("MSFT", 2024, quarter=2)
        """
        return get_geographic_revenue(
            company=company,
            year=year,
            quarter=quarter,
            user_agent=user_agent
        )
    
    @mcp.tool("extract_business_metrics")
    def extract_business_metrics_tool(
        company: str,
        metrics: List[str],
        periods: int = 4,
        user_agent: str = user_agent
    ) -> Dict[str, Any]:
        """
        Extract specific business metrics from recent filings.
        
        Parameters:
            company: Company ticker or CIK
            metrics: List of metric names to search for
            periods: Number of periods to analyze
            user_agent: User agent string required by the SEC
            
        Returns:
            Dictionary containing requested metrics over time
            
        Example:
            extract_business_metrics("NFLX", ["subscribers", "ARPU"], periods=8)
        """
        return extract_business_metrics(
            company=company,
            metrics=metrics,
            periods=periods,
            user_agent=user_agent
        )
    
    @mcp.tool("analyze_revenue_trends")
    def analyze_revenue_trends_tool(
        company: str,
        segment: Optional[str] = None,
        years_back: int = 3,
        user_agent: str = user_agent
    ) -> Dict[str, Any]:
        """
        Analyze revenue trends for company or specific segment.
        
        Parameters:
            company: Company ticker or CIK
            segment: Optional specific segment to analyze
            years_back: Number of years to analyze
            user_agent: User agent string required by the SEC
            
        Returns:
            Dictionary containing trend analysis and growth rates
            
        Example:
            analyze_revenue_trends("AMZN", segment="AWS", years_back=5)
        """
        return analyze_revenue_trends(
            company=company,
            segment=segment,
            years_back=years_back,
            user_agent=user_agent
        )


@cached(filing_type='10k')
@rate_limited
def get_product_revenue(
    company: str,
    product_name: str,
    start_year: int,
    end_year: Optional[int] = None,
    user_agent: str = None
) -> Dict[str, Any]:
    """Extract product/segment revenue from filings."""
    
    if not end_year:
        end_year = datetime.now().year
    
    revenue_data = []
    
    try:
        # Get 10-K filings for the period
        start_date = date(start_year, 1, 1)
        end_date = date(end_year, 12, 31)
        
        annual_filings = filings(
            cik_lookup=company,
            filing_type=FilingType.FILING_10K,
            user_agent=user_agent,
            start_date=start_date,
            end_date=end_date
        )
        
        # Also get 10-Q filings for quarterly data
        quarterly_filings = filings(
            cik_lookup=company,
            filing_type=FilingType.FILING_10Q,
            user_agent=user_agent,
            start_date=start_date,
            end_date=end_date,
            count=12  # Last 12 quarters
        )
        
        # For simplified implementation, return structure
        # Full implementation would parse segment tables from filings
        
        return {
            "company": company,
            "product_name": product_name,
            "period": {
                "start": start_year,
                "end": end_year
            },
            "revenue_data": [],
            "total_revenue_period": 0,
            "average_growth_rate": None,
            "message": "Segment revenue parsing implementation pending"
        }
        
    except Exception as e:
        logger.error(f"Error getting product revenue: {e}")
        return {
            "error": str(e),
            "company": company,
            "product_name": product_name
        }


@cached(filing_type='10q')
def get_geographic_revenue(
    company: str,
    year: int,
    quarter: Optional[int] = None,
    user_agent: str = None
) -> Dict[str, Any]:
    """Extract geographic revenue breakdown."""
    
    filing_type = FilingType.FILING_10K if quarter is None else FilingType.FILING_10Q
    
    return {
        "company": company,
        "year": year,
        "quarter": quarter,
        "geographic_breakdown": [],
        "total_revenue": 0,
        "message": "Geographic revenue parsing implementation pending"
    }


def extract_business_metrics(
    company: str,
    metrics: List[str],
    periods: int = 4,
    user_agent: str = None
) -> Dict[str, Any]:
    """Extract specific business metrics from filings."""
    
    return {
        "company": company,
        "metrics_requested": metrics,
        "periods": periods,
        "metrics_data": {},
        "message": "Business metrics extraction implementation pending"
    }


def analyze_revenue_trends(
    company: str,
    segment: Optional[str] = None,
    years_back: int = 3,
    user_agent: str = None
) -> Dict[str, Any]:
    """Analyze revenue trends over time."""
    
    return {
        "company": company,
        "segment": segment or "Total Revenue",
        "years_analyzed": years_back,
        "trend_analysis": {
            "growth_rate": None,
            "volatility": None,
            "seasonality": None
        },
        "message": "Revenue trend analysis implementation pending"
    }


def parse_segment_table(html_content: str) -> List[Dict[str, Any]]:
    """Parse segment revenue table from HTML filing content."""
    
    soup = BeautifulSoup(html_content, 'html.parser')
    segments = []
    
    # Common patterns for segment tables
    # This is highly company-specific and would need extensive patterns
    
    # Look for tables with segment keywords
    for table in soup.find_all('table'):
        table_text = table.get_text().lower()
        if any(keyword in table_text for keyword in ['segment', 'revenue', 'sales', 'product']):
            # Extract table data
            # This would need sophisticated parsing logic
            pass
    
    return segments


def extract_revenue_from_xbrl(xbrl_content: str, segment_name: str) -> Optional[float]:
    """Extract revenue value from XBRL content for a specific segment."""
    
    # This would parse XBRL tags for segment data
    # Example: us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax
    
    return None