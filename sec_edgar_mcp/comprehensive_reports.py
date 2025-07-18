"""Comprehensive entity reports combining all SEC data sources."""

import logging
from typing import List, Dict, Any, Optional
from datetime import date, datetime, timedelta
from mcp.server.fastmcp import FastMCP

from .cross_company_search import get_all_insider_companies
from .proxy_parser import get_current_board_from_proxy
from .insider_tools import get_insider_transactions, get_recent_insider_activity
from .institutional_tools import search_institutional_ownership
from .models import ComprehensiveInsiderProfile, PersonCompanyMapping, BoardPosition
from .name_matching import name_matcher
from .utils import rate_limited, cached

logger = logging.getLogger(__name__)


def register_comprehensive_report_tools(mcp: FastMCP, user_agent: str):
    """Register comprehensive report tools with the MCP server."""
    
    @mcp.tool("generate_comprehensive_insider_report")
    def generate_comprehensive_insider_report_tool(
        person_name: str,
        include_former: bool = True,
        years_back: int = 10,
        user_agent: str = user_agent
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive insider report combining all available data sources.
        
        This addresses the "entity report limitations" by providing working
        cross-company analysis functionality.
        
        Parameters:
            person_name: Full name of the person
            include_former: Include former positions and companies
            years_back: How many years to analyze (default: 10)
            user_agent: User agent string required by the SEC
            
        Returns:
            Comprehensive report with cross-company analysis, board positions,
            transaction history, and timeline of activities
            
        Example:
            generate_comprehensive_insider_report("Gale Klappa", include_former=True)
        """
        return generate_comprehensive_insider_report(
            person_name=person_name,
            include_former=include_former,
            years_back=years_back,
            user_agent=user_agent
        )
    
    @mcp.tool("analyze_board_position_timeline")
    def analyze_board_position_timeline_tool(
        person_name: str,
        user_agent: str = user_agent
    ) -> Dict[str, Any]:
        """
        Analyze timeline of board positions with appointment/resignation tracking.
        
        Parameters:
            person_name: Full name of the person
            user_agent: User agent string required by the SEC
            
        Returns:
            Timeline analysis of board positions including current vs former status
            
        Example:
            analyze_board_position_timeline("Gale Klappa")
        """
        return analyze_board_position_timeline(
            person_name=person_name,
            user_agent=user_agent
        )
    
    @mcp.tool("compare_insider_across_companies")
    def compare_insider_across_companies_tool(
        person_name: str,
        user_agent: str = user_agent
    ) -> Dict[str, Any]:
        """
        Compare insider's activity and positions across multiple companies.
        
        Parameters:
            person_name: Full name of the person
            user_agent: User agent string required by the SEC
            
        Returns:
            Comparative analysis across companies
            
        Example:
            compare_insider_across_companies("Gale Klappa")
        """
        return compare_insider_across_companies(
            person_name=person_name,
            user_agent=user_agent
        )


@cached(filing_type='comprehensive_report')
@rate_limited
def generate_comprehensive_insider_report(
    person_name: str,
    include_former: bool = True,
    years_back: int = 10,
    user_agent: str = None
) -> Dict[str, Any]:
    """Generate comprehensive insider report combining all data sources."""
    
    logger.info(f"Generating comprehensive insider report for {person_name}")
    
    report_data = {
        "person_name": person_name,
        "report_date": date.today().isoformat(),
        "analysis_period_years": years_back,
        "data_sources": []
    }
    
    try:
        # 1. Cross-company insider search
        logger.info("Step 1: Cross-company insider search")
        cross_company_result = get_all_insider_companies(
            person_name=person_name,
            include_former=include_former,
            years_back=years_back,
            user_agent=user_agent
        )
        
        report_data["cross_company_summary"] = cross_company_result.get("summary", {})
        report_data["companies"] = cross_company_result.get("companies", [])
        report_data["data_sources"].append("Form 4 (Insider Transactions)")
        
        # 2. Current board positions from proxy statements
        logger.info("Step 2: Current board positions from proxy statements")
        current_board_positions = []
        
        for company in report_data["companies"]:
            if company.get("position_status") == "current":
                try:
                    proxy_positions = get_current_board_from_proxy(
                        company=company["ticker"],
                        user_agent=user_agent
                    )
                    
                    # Filter positions for this person
                    person_positions = [
                        pos for pos in proxy_positions
                        if name_matcher.is_name_match(person_name, pos.person_name)
                    ]
                    
                    current_board_positions.extend([pos.to_dict() for pos in person_positions])
                    
                except Exception as e:
                    logger.debug(f"Could not get proxy data for {company['ticker']}: {e}")
        
        report_data["current_board_positions"] = current_board_positions
        if current_board_positions:
            report_data["data_sources"].append("DEF 14A (Proxy Statements)")
        
        # 3. Detailed transaction analysis per company
        logger.info("Step 3: Detailed transaction analysis")
        detailed_transactions = {}
        
        for company in report_data["companies"]:
            try:
                detailed_result = get_insider_transactions(
                    person_name=person_name,
                    company=company["ticker"],
                    start_date=(date.today() - timedelta(days=years_back * 365)).isoformat(),
                    end_date=date.today().isoformat(),
                    user_agent=user_agent
                )
                
                if detailed_result.get("transaction_count", 0) > 0:
                    detailed_transactions[company["ticker"]] = {
                        "company_name": company["company_name"],
                        "transaction_details": detailed_result["transactions"],
                        "summary": detailed_result["summary"]
                    }
                    
            except Exception as e:
                logger.debug(f"Error getting detailed transactions for {company['ticker']}: {e}")
        
        report_data["detailed_transactions"] = detailed_transactions
        
        # 4. Board position timeline analysis
        logger.info("Step 4: Board position timeline analysis")
        timeline_analysis = analyze_board_position_timeline(
            person_name=person_name,
            user_agent=user_agent
        )
        
        report_data["board_position_timeline"] = timeline_analysis
        
        # 5. Key insights and summary
        logger.info("Step 5: Generating insights")
        insights = generate_key_insights(report_data)
        report_data["key_insights"] = insights
        
        # 6. Current vs former analysis
        current_companies = [c for c in report_data["companies"] if c.get("position_status") == "current"]
        former_companies = [c for c in report_data["companies"] if c.get("position_status") == "former"]
        
        report_data["position_analysis"] = {
            "current_companies": len(current_companies),
            "former_companies": len(former_companies),
            "current_company_list": [f"{c['company_name']} ({c['ticker']})" for c in current_companies],
            "former_company_list": [f"{c['company_name']} ({c['ticker']})" for c in former_companies],
            "total_unique_companies": len(set(c["ticker"] for c in report_data["companies"]))
        }
        
        logger.info(f"Comprehensive report generated successfully for {person_name}")
        
        return report_data
        
    except Exception as e:
        logger.error(f"Error generating comprehensive report: {e}")
        return {
            "person_name": person_name,
            "error": str(e),
            "report_date": date.today().isoformat()
        }


def analyze_board_position_timeline(person_name: str, user_agent: str = None) -> Dict[str, Any]:
    """Analyze timeline of board positions with appointment/resignation tracking."""
    
    logger.info(f"Analyzing board position timeline for {person_name}")
    
    # Get cross-company data first
    cross_company_result = get_all_insider_companies(
        person_name=person_name,
        include_former=True,
        years_back=15,  # Look back further for timeline
        user_agent=user_agent
    )
    
    timeline_events = []
    
    for company in cross_company_result.get("companies", []):
        # Create timeline events based on transaction data
        transaction_summary = company.get("transaction_summary", {})
        
        first_transaction = transaction_summary.get("first_transaction")
        last_transaction = transaction_summary.get("last_transaction")
        
        if first_transaction:
            timeline_events.append({
                "date": first_transaction,
                "event_type": "first_transaction",
                "company": company["company_name"],
                "ticker": company["ticker"],
                "description": f"First insider transaction at {company['company_name']}"
            })
        
        if last_transaction and last_transaction != first_transaction:
            timeline_events.append({
                "date": last_transaction,
                "event_type": "last_transaction",
                "company": company["company_name"],
                "ticker": company["ticker"],
                "description": f"Most recent transaction at {company['company_name']}"
            })
        
        # Estimate appointment/departure based on position status
        if company.get("position_status") == "former" and last_transaction:
            timeline_events.append({
                "date": last_transaction,
                "event_type": "estimated_departure",
                "company": company["company_name"],
                "ticker": company["ticker"],
                "description": f"Estimated departure from {company['company_name']} board (based on last transaction)"
            })
    
    # Sort timeline events by date
    timeline_events.sort(key=lambda x: x["date"])
    
    # Calculate career statistics
    career_stats = {
        "total_companies": len(cross_company_result.get("companies", [])),
        "current_positions": len([c for c in cross_company_result.get("companies", []) if c.get("position_status") == "current"]),
        "former_positions": len([c for c in cross_company_result.get("companies", []) if c.get("position_status") == "former"]),
        "career_span_years": calculate_career_span(timeline_events),
        "average_tenure": calculate_average_tenure(cross_company_result.get("companies", []))
    }
    
    return {
        "person_name": person_name,
        "analysis_date": date.today().isoformat(),
        "timeline_events": timeline_events,
        "career_statistics": career_stats,
        "position_changes": len(timeline_events),
        "companies_timeline": create_companies_timeline(cross_company_result.get("companies", []))
    }


def compare_insider_across_companies(person_name: str, user_agent: str = None) -> Dict[str, Any]:
    """Compare insider's activity and positions across multiple companies."""
    
    logger.info(f"Comparing insider activity across companies for {person_name}")
    
    # Get comprehensive data
    cross_company_result = get_all_insider_companies(
        person_name=person_name,
        include_former=True,
        years_back=10,
        user_agent=user_agent
    )
    
    companies = cross_company_result.get("companies", [])
    
    if not companies:
        return {
            "person_name": person_name,
            "message": "No companies found for comparison",
            "comparison_date": date.today().isoformat()
        }
    
    # Calculate comparative metrics
    comparison_metrics = []
    
    for company in companies:
        transaction_summary = company.get("transaction_summary", {})
        
        metrics = {
            "company_name": company["company_name"],
            "ticker": company["ticker"],
            "position_status": company["position_status"],
            "current_position": company.get("current_position"),
            "total_transactions": transaction_summary.get("total_transactions", 0),
            "shares_bought": transaction_summary.get("shares_bought", 0),
            "shares_sold": transaction_summary.get("shares_sold", 0),
            "net_shares": transaction_summary.get("net_shares", 0),
            "first_transaction": transaction_summary.get("first_transaction"),
            "last_transaction": transaction_summary.get("last_transaction"),
            "activity_level": classify_activity_level(transaction_summary.get("total_transactions", 0)),
            "net_position": "Buyer" if transaction_summary.get("net_shares", 0) > 0 else "Seller" if transaction_summary.get("net_shares", 0) < 0 else "Neutral"
        }
        
        comparison_metrics.append(metrics)
    
    # Sort by activity level
    comparison_metrics.sort(key=lambda x: x["total_transactions"], reverse=True)
    
    # Generate summary insights
    summary_insights = {
        "most_active_company": comparison_metrics[0]["company_name"] if comparison_metrics else None,
        "total_transactions_all_companies": sum(m["total_transactions"] for m in comparison_metrics),
        "net_buyer_companies": len([m for m in comparison_metrics if m["net_position"] == "Buyer"]),
        "net_seller_companies": len([m for m in comparison_metrics if m["net_position"] == "Seller"]),
        "current_positions_count": len([m for m in comparison_metrics if m["position_status"] == "current"]),
        "average_transactions_per_company": sum(m["total_transactions"] for m in comparison_metrics) / len(comparison_metrics) if comparison_metrics else 0
    }
    
    return {
        "person_name": person_name,
        "comparison_date": date.today().isoformat(),
        "companies_compared": len(comparison_metrics),
        "comparison_metrics": comparison_metrics,
        "summary_insights": summary_insights,
        "ranking": {
            "by_activity": sorted(comparison_metrics, key=lambda x: x["total_transactions"], reverse=True)[:5],
            "by_net_shares": sorted(comparison_metrics, key=lambda x: abs(x["net_shares"]), reverse=True)[:5]
        }
    }


def generate_key_insights(report_data: Dict[str, Any]) -> List[str]:
    """Generate key insights from comprehensive report data."""
    insights = []
    
    # Cross-company insights
    summary = report_data.get("cross_company_summary", {})
    
    if summary.get("total_companies", 0) > 1:
        insights.append(f"Multi-company insider with positions at {summary['total_companies']} companies")
    
    if summary.get("active_positions", 0) > 0:
        insights.append(f"Currently active at {summary['active_positions']} companies")
    
    if summary.get("former_positions", 0) > 0:
        insights.append(f"Former positions at {summary['former_positions']} companies")
    
    # Transaction insights
    if summary.get("total_transactions", 0) > 50:
        insights.append("High-activity insider with 50+ transactions")
    elif summary.get("total_transactions", 0) > 20:
        insights.append("Moderate-activity insider with 20+ transactions")
    
    # Board position insights
    current_positions = report_data.get("current_board_positions", [])
    if current_positions:
        insights.append(f"Currently serves on {len(current_positions)} board(s) based on proxy statements")
    
    return insights


def calculate_career_span(timeline_events: List[Dict]) -> Optional[int]:
    """Calculate career span in years from timeline events."""
    if not timeline_events:
        return None
    
    dates = [event["date"] for event in timeline_events if event["date"]]
    if not dates:
        return None
    
    from datetime import datetime
    date_objects = [datetime.fromisoformat(d).date() for d in dates]
    
    earliest = min(date_objects)
    latest = max(date_objects)
    
    return (latest - earliest).days // 365


def calculate_average_tenure(companies: List[Dict]) -> Optional[float]:
    """Calculate average tenure across companies."""
    if not companies:
        return None
    
    tenures = []
    
    for company in companies:
        transaction_summary = company.get("transaction_summary", {})
        first = transaction_summary.get("first_transaction")
        last = transaction_summary.get("last_transaction")
        
        if first and last:
            from datetime import datetime
            first_date = datetime.fromisoformat(first).date()
            last_date = datetime.fromisoformat(last).date()
            tenure_years = (last_date - first_date).days / 365.25
            tenures.append(tenure_years)
    
    return sum(tenures) / len(tenures) if tenures else None


def classify_activity_level(transaction_count: int) -> str:
    """Classify activity level based on transaction count."""
    if transaction_count >= 50:
        return "Very High"
    elif transaction_count >= 20:
        return "High"
    elif transaction_count >= 10:
        return "Moderate"
    elif transaction_count >= 5:
        return "Low"
    else:
        return "Very Low"


def create_companies_timeline(companies: List[Dict]) -> List[Dict]:
    """Create a timeline view of companies."""
    timeline = []
    
    for company in companies:
        transaction_summary = company.get("transaction_summary", {})
        
        entry = {
            "company": company["company_name"],
            "ticker": company["ticker"],
            "status": company.get("position_status", "unknown"),
            "first_activity": transaction_summary.get("first_transaction"),
            "last_activity": transaction_summary.get("last_transaction"),
            "total_transactions": transaction_summary.get("total_transactions", 0)
        }
        
        timeline.append(entry)
    
    # Sort by first activity date
    timeline.sort(key=lambda x: x["first_activity"] or "9999-12-31")
    
    return timeline