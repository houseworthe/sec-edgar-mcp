"""Unified search interface for high-level SEC EDGAR queries."""

import logging
from typing import Dict, Any, List, Optional
from datetime import date, timedelta
from mcp.server.fastmcp import FastMCP

from .insider_tools import get_insider_transactions, get_recent_insider_activity
from .institutional_tools import get_13f_holdings, search_institutional_ownership, get_major_shareholders
from .financial_parser import get_product_revenue, analyze_revenue_trends
from .models import OwnershipSummary

logger = logging.getLogger(__name__)


def register_unified_tools(mcp: FastMCP, user_agent: str):
    """Register unified search tools with the MCP server."""
    
    @mcp.tool("answer_ownership_question")
    def answer_ownership_question_tool(
        entity_name: str,
        company: str,
        include_history: bool = False,
        user_agent: str = user_agent
    ) -> Dict[str, Any]:
        """
        Answer "How many shares of X does Y own?" by combining all ownership sources.
        
        Parameters:
            entity_name: Name of person or institution
            company: Company ticker or name
            include_history: Include historical ownership changes
            user_agent: User agent string required by the SEC
            
        Returns:
            Comprehensive ownership summary combining insider and institutional data
            
        Example:
            answer_ownership_question("Warren Buffett", "AAPL", include_history=True)
        """
        return answer_ownership_question(
            entity_name=entity_name,
            company=company,
            include_history=include_history,
            user_agent=user_agent
        )
    
    @mcp.tool("answer_sales_question")
    def answer_sales_question_tool(
        company: str,
        product_or_segment: str,
        time_period: str = "1Y",
        user_agent: str = user_agent
    ) -> Dict[str, Any]:
        """
        Answer "How much has X sold of Y?" by analyzing segment revenue data.
        
        Parameters:
            company: Company ticker or name
            product_or_segment: Product name or business segment
            time_period: Time period to analyze (1Y, 2Y, 3Y, 5Y)
            user_agent: User agent string required by the SEC
            
        Returns:
            Revenue analysis for the specified product/segment
            
        Example:
            answer_sales_question("AAPL", "iPhone", "2Y")
        """
        return answer_sales_question(
            company=company,
            product_or_segment=product_or_segment,
            time_period=time_period,
            user_agent=user_agent
        )
    
    @mcp.tool("generate_entity_report")
    def generate_entity_report_tool(
        entity_names: List[str],
        activity_types: List[str] = ["all"],
        days_back: int = 90,
        user_agent: str = user_agent
    ) -> Dict[str, Any]:
        """
        Generate comprehensive activity report for multiple entities.
        
        Parameters:
            entity_names: List of person/company names to analyze
            activity_types: Types of activity to include (insider, institutional, filings, all)
            days_back: Number of days to look back
            user_agent: User agent string required by the SEC
            
        Returns:
            Comprehensive activity report for all entities
            
        Example:
            generate_entity_report(["Elon Musk", "Jeff Bezos"], activity_types=["insider"])
        """
        return generate_entity_report(
            entity_names=entity_names,
            activity_types=activity_types,
            days_back=days_back,
            user_agent=user_agent
        )


def answer_ownership_question(
    entity_name: str,
    company: str,
    include_history: bool = False,
    user_agent: str = None
) -> Dict[str, Any]:
    """Combine all ownership data sources to answer ownership questions."""
    
    ownership_data = {
        "entity_name": entity_name,
        "company": company,
        "as_of_date": date.today().isoformat(),
        "ownership_summary": {
            "total_shares": 0,
            "ownership_percentage": None,
            "value_at_current_price": None
        },
        "ownership_breakdown": {
            "insider_holdings": None,
            "institutional_holdings": None,
            "other_holdings": None
        },
        "recent_changes": [],
        "data_sources": []
    }
    
    # Check if entity is an individual (potential insider)
    if not any(corp_word in entity_name.lower() for corp_word in ['corp', 'inc', 'llc', 'fund', 'capital', 'partners']):
        # Search for insider holdings
        insider_data = get_recent_insider_activity(
            company=company,
            days_back=365 if include_history else 90,
            user_agent=user_agent
        )
        
        # Look for the specific person in insider data
        for insider_name, data in insider_data.get("insiders", {}).items():
            if entity_name.lower() in insider_name.lower():
                ownership_data["ownership_breakdown"]["insider_holdings"] = {
                    "shares": data.get("net_shares", 0),
                    "recent_activity": data.get("transactions", [])[:5]
                }
                ownership_data["data_sources"].append("Form 4 filings")
    
    # Check for institutional holdings
    else:
        # Search for institutional holdings
        inst_data = get_13f_holdings(
            institution=entity_name,
            user_agent=user_agent
        )
        
        ownership_data["ownership_breakdown"]["institutional_holdings"] = inst_data
        ownership_data["data_sources"].append("13F filings")
    
    # Check for major shareholder filings (13D/13G)
    major_holder_data = get_major_shareholders(
        company=company,
        user_agent=user_agent
    )
    
    # Calculate totals
    total_shares = 0
    if ownership_data["ownership_breakdown"]["insider_holdings"]:
        total_shares += ownership_data["ownership_breakdown"]["insider_holdings"].get("shares", 0)
    
    ownership_data["ownership_summary"]["total_shares"] = total_shares
    
    return ownership_data


def answer_sales_question(
    company: str,
    product_or_segment: str,
    time_period: str = "1Y",
    user_agent: str = None
) -> Dict[str, Any]:
    """Analyze product/segment sales data."""
    
    # Parse time period
    years = int(time_period[0]) if time_period[0].isdigit() else 1
    end_year = date.today().year
    start_year = end_year - years
    
    # Get product revenue data
    revenue_data = get_product_revenue(
        company=company,
        product_name=product_or_segment,
        start_year=start_year,
        end_year=end_year,
        user_agent=user_agent
    )
    
    # Analyze trends
    trend_analysis = analyze_revenue_trends(
        company=company,
        segment=product_or_segment,
        years_back=years,
        user_agent=user_agent
    )
    
    return {
        "company": company,
        "product_or_segment": product_or_segment,
        "time_period": time_period,
        "revenue_summary": revenue_data,
        "trend_analysis": trend_analysis,
        "data_sources": ["10-K filings", "10-Q filings"]
    }


def generate_entity_report(
    entity_names: List[str],
    activity_types: List[str] = ["all"],
    days_back: int = 90,
    user_agent: str = None
) -> Dict[str, Any]:
    """Generate comprehensive activity report for multiple entities."""
    
    reports = {}
    
    for entity in entity_names:
        entity_report = {
            "entity_name": entity,
            "report_period": {
                "start": (date.today() - timedelta(days=days_back)).isoformat(),
                "end": date.today().isoformat()
            },
            "activities": {}
        }
        
        # Check for insider trading activity
        if "all" in activity_types or "insider" in activity_types:
            # Search across multiple companies for this person
            # For now, simplified implementation
            entity_report["activities"]["insider_trading"] = {
                "transactions": [],
                "summary": "Cross-company search pending implementation"
            }
        
        # Check for institutional activity
        if "all" in activity_types or "institutional" in activity_types:
            if any(corp_word in entity.lower() for corp_word in ['corp', 'inc', 'llc', 'fund', 'capital']):
                entity_report["activities"]["institutional"] = {
                    "holdings": [],
                    "recent_changes": []
                }
        
        reports[entity] = entity_report
    
    return {
        "entities_analyzed": len(entity_names),
        "report_period_days": days_back,
        "activity_types": activity_types,
        "entity_reports": reports
    }