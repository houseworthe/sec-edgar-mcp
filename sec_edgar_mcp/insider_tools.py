"""MCP tools for insider trading analysis using SEC Form 4 filings."""

import logging
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, date, timedelta
from secedgar import filings, FilingType
from mcp.server.fastmcp import FastMCP

from .form4_parser import Form4Parser
from .models import InsiderTransaction
from .utils import (
    normalize_cik, normalize_ticker, cached, rate_limited,
    build_filing_url, extract_xml_url, parse_date
)
from .config import initialize_config

logger = logging.getLogger(__name__)


def register_insider_tools(mcp: FastMCP, user_agent: str):
    """Register all insider trading tools with the MCP server."""
    
    @mcp.tool("get_insider_transactions")
    def get_insider_transactions_tool(
        person_name: str,
        company: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        transaction_types: Optional[List[str]] = None,
        user_agent: str = user_agent
    ) -> Dict[str, Any]:
        """
        Get all Form 4 filings for a specific insider by name.
        
        Parameters:
            person_name: Name of the insider to search for
            company: Optional company ticker or CIK to filter by
            start_date: Start date for search (YYYY-MM-DD format)
            end_date: End date for search (YYYY-MM-DD format)
            transaction_types: Optional list of transaction types to filter (PURCHASE, SALE, etc.)
            user_agent: User agent string required by the SEC
            
        Returns:
            Dictionary containing insider transactions and summary statistics
            
        Example:
            Get all transactions by Elon Musk at Tesla in 2024:
            get_insider_transactions("Elon Musk", "TSLA", "2024-01-01", "2024-12-31")
        """
        return get_insider_transactions(
            person_name=person_name,
            company=company,
            start_date=start_date,
            end_date=end_date,
            transaction_types=transaction_types,
            user_agent=user_agent
        )
    
    @mcp.tool("get_form4_details")
    def get_form4_details_tool(
        accession_number: str,
        user_agent: str = user_agent
    ) -> Dict[str, Any]:
        """
        Parse a specific Form 4 filing to extract detailed transaction information.
        
        Parameters:
            accession_number: SEC accession number for the Form 4 filing
            user_agent: User agent string required by the SEC
            
        Returns:
            Dictionary containing parsed transaction details from the Form 4
            
        Example:
            get_form4_details("0001209191-24-001234")
        """
        return get_form4_details(
            accession_number=accession_number,
            user_agent=user_agent
        )
    
    
    @mcp.tool("get_recent_insider_activity")
    def get_recent_insider_activity_tool(
        company: str,
        days_back: int = 90,
        min_transaction_value: Optional[float] = None,
        user_agent: str = user_agent
    ) -> Dict[str, Any]:
        """
        Get recent insider trading activity for a specific company.
        
        Parameters:
            company: Company ticker or CIK
            days_back: Number of days to look back (default: 90)
            min_transaction_value: Minimum transaction value to include
            user_agent: User agent string required by the SEC
            
        Returns:
            Dictionary containing recent insider transactions and analysis
            
        Example:
            get_recent_insider_activity("AAPL", days_back=30, min_transaction_value=100000)
        """
        return get_recent_insider_activity(
            company=company,
            days_back=days_back,
            min_transaction_value=min_transaction_value,
            user_agent=user_agent
        )
    
    @mcp.tool("analyze_insider_patterns")
    def analyze_insider_patterns_tool(
        company: str,
        time_period: str = "1Y",
        user_agent: str = user_agent
    ) -> Dict[str, Any]:
        """
        Analyze patterns in insider trading for a company over a time period.
        
        Parameters:
            company: Company ticker or CIK
            time_period: Time period to analyze (1M, 3M, 6M, 1Y, 2Y, 5Y)
            user_agent: User agent string required by the SEC
            
        Returns:
            Dictionary containing pattern analysis including buy/sell ratios,
            seasonal trends, and top insiders by activity
            
        Example:
            analyze_insider_patterns("MSFT", "6M")
        """
        return analyze_insider_patterns(
            company=company,
            time_period=time_period,
            user_agent=user_agent
        )


@cached(filing_type='form4')
@rate_limited
def get_insider_transactions(
    person_name: str,
    company: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    transaction_types: Optional[List[str]] = None,
    user_agent: str = None
) -> Dict[str, Any]:
    """Implementation of get_insider_transactions tool."""
    
    parser = Form4Parser(user_agent)
    transactions = []
    
    # Parse dates - default to 2 years back to catch more transactions
    start = parse_date(start_date) if start_date else date.today() - timedelta(days=730)  # 2 years
    end = parse_date(end_date) if end_date else date.today()
    
    logger.info(f"Searching for insider transactions: {person_name} at {company} from {start} to {end}")
    
    try:
        # If company is specified, search within that company
        if company:
            # Get Form 4 filings for the company
            company_filings = filings(
                cik_lookup=company,
                filing_type=FilingType.FILING_4,
                user_agent=user_agent,
                start_date=start,
                end_date=end
            )
            
            # Get filing URLs
            try:
                urls_dict = company_filings.get_urls()
                # The URLs are returned as a dict with company as key
                if isinstance(urls_dict, dict):
                    # Get the URLs for the first (and likely only) key
                    company_key = list(urls_dict.keys())[0] if urls_dict else None
                    filing_urls = urls_dict.get(company_key, []) if company_key else []
                else:
                    filing_urls = list(urls_dict) if urls_dict else []
            except Exception as e:
                logger.error(f"Error getting filing URLs: {e}")
                filing_urls = []
            
            # Deduplicate URLs (secedgar sometimes returns duplicates)
            filing_urls = list(dict.fromkeys(filing_urls))  # Preserves order while removing duplicates
            
            logger.info(f"Found {len(filing_urls)} Form 4 filings for {company}")
            
            # Process each filing
            for i, filing_url in enumerate(filing_urls[:100]):  # Limit to recent 100 filings
                try:
                    # Extract accession number from URL
                    accession = filing_url.split('/')[-2]
                    
                    # For Form 4, we need the primary document XML
                    # The URL might be to an index page, we need the actual Form 4 XML
                    if not filing_url.endswith('.xml'):
                        # First, fetch the index to find the XML filename
                        index_content = parser.fetch_filing_content(filing_url)
                        if index_content and '<FILENAME>' in index_content:
                            # Look for XML filename in the index
                            import re
                            xml_match = re.search(r'<FILENAME>([^<]+\.xml)', index_content)
                            if xml_match:
                                xml_filename = xml_match.group(1)
                                base_url = filing_url.rsplit('/', 1)[0]
                                xml_url = f"{base_url}/{xml_filename}"
                            else:
                                # Default to doc1.xml if no match
                                base_url = filing_url.rsplit('/', 1)[0]
                                xml_url = f"{base_url}/doc1.xml"
                        else:
                            # Fallback
                            base_url = filing_url.rsplit('/', 1)[0]
                            xml_url = f"{base_url}/doc1.xml"
                    else:
                        xml_url = filing_url
                    
                    logger.debug(f"Processing filing {i+1}/{min(len(filing_urls), 100)}: {xml_url}")
                    
                    # Fetch and parse filing
                    xml_content = parser.fetch_filing_content(xml_url)
                    if xml_content:
                        # Check if this filing contains the person's name before parsing
                        # Need to check both "First Last" and "Last First" formats
                        name_parts = person_name.lower().split()
                        xml_lower = xml_content.lower()
                        
                        # Check various name formats
                        name_found = False
                        if person_name.lower() in xml_lower:
                            name_found = True
                        elif len(name_parts) >= 2:
                            # Try reversed name (Last First)
                            reversed_name = f"{name_parts[-1]} {' '.join(name_parts[:-1])}"
                            if reversed_name in xml_lower:
                                name_found = True
                            # Try just last name
                            elif name_parts[-1] in xml_lower:
                                name_found = True
                        
                        if name_found:
                            logger.info(f"Found potential match for {person_name} in filing {accession}")
                            filing_transactions = parser.parse_form4_xml(xml_content, accession)
                            
                            if filing_transactions:
                                logger.info(f"Extracted {len(filing_transactions)} transactions from {accession}")
                            else:
                                logger.warning(f"No transactions extracted from {accession} despite name match")
                            
                            # Filter by person name (with better matching)
                            for trans in filing_transactions:
                                # Normalize names for comparison
                                normalized_search = person_name.lower().replace('.', '').replace(',', '').strip()
                                normalized_insider = trans.insider_name.lower().replace('.', '').replace(',', '').strip()
                                
                                # Check exact match or substring match
                                if normalized_search in normalized_insider or normalized_insider in normalized_search:
                                    logger.info(f"Matched transaction for {trans.insider_name} on {trans.transaction_date}")
                                    transactions.append(trans)
                                else:
                                    # Try matching individual name parts
                                    search_parts = normalized_search.split()
                                    insider_parts = normalized_insider.split()
                                    
                                    # Check if all parts of search name are in insider name
                                    if all(any(sp in ip for ip in insider_parts) for sp in search_parts):
                                        logger.info(f"Matched transaction for {trans.insider_name} on {trans.transaction_date} (partial match)")
                                        transactions.append(trans)
                
                except Exception as e:
                    logger.error(f"Error processing filing {filing_url}: {e}")
        
        else:
            # Without company filter, this is more challenging
            # Would need to search across all companies - implement if needed
            logger.warning("Searching across all companies not yet implemented")
    
    except Exception as e:
        logger.error(f"Error getting insider transactions: {e}")
    
    # Filter by transaction types if specified
    if transaction_types:
        type_filter = [t.upper() for t in transaction_types]
        transactions = [t for t in transactions if t.transaction_type.name in type_filter]
    
    # Sort by date
    transactions.sort(key=lambda x: x.transaction_date, reverse=True)
    
    # Calculate summary statistics
    summary = calculate_insider_summary(transactions)
    
    return {
        "insider_name": person_name,
        "company": company,
        "date_range": {
            "start": start.isoformat(),
            "end": end.isoformat()
        },
        "transaction_count": len(transactions),
        "transactions": [t.to_dict() for t in transactions],
        "summary": summary
    }


@rate_limited
def get_form4_details(
    accession_number: str,
    user_agent: str = None
) -> Dict[str, Any]:
    """Implementation of get_form4_details tool."""
    
    parser = Form4Parser(user_agent)
    
    try:
        # Build URL for the filing
        # Extract CIK from accession number format: 0001234567-24-123456
        parts = accession_number.split('-')
        if len(parts) >= 3:
            cik = parts[0]
            
            # Build filing URL
            primary_doc = f"{accession_number}.txt"
            filing_url = build_filing_url(cik, accession_number, primary_doc)
            xml_url = extract_xml_url(filing_url)
            
            # Fetch and parse
            xml_content = parser.fetch_filing_content(xml_url)
            if xml_content:
                transactions = parser.parse_form4_xml(xml_content, accession_number)
                
                if transactions:
                    # Group by insider (in case of multiple insiders in one filing)
                    insider_groups = {}
                    for trans in transactions:
                        key = trans.insider_name
                        if key not in insider_groups:
                            insider_groups[key] = []
                        insider_groups[key].append(trans)
                    
                    return {
                        "accession_number": accession_number,
                        "filing_url": filing_url,
                        "insider_count": len(insider_groups),
                        "transaction_count": len(transactions),
                        "insiders": {
                            name: {
                                "transactions": [t.to_dict() for t in trans_list],
                                "summary": calculate_insider_summary(trans_list)
                            }
                            for name, trans_list in insider_groups.items()
                        }
                    }
        
        return {
            "error": f"Could not parse Form 4 with accession number {accession_number}"
        }
    
    except Exception as e:
        logger.error(f"Error getting Form 4 details: {e}")
        return {
            "error": str(e),
            "accession_number": accession_number
        }




@cached(filing_type='form4')
@rate_limited
def get_recent_insider_activity(
    company: str,
    days_back: int = 90,
    min_transaction_value: Optional[float] = None,
    user_agent: str = None
) -> Dict[str, Any]:
    """Implementation of get_recent_insider_activity tool."""
    
    parser = Form4Parser(user_agent)
    transactions = []
    
    # Calculate date range
    end_date = date.today()
    start_date = end_date - timedelta(days=days_back)
    
    try:
        # Get Form 4 filings for the company
        company_filings = filings(
            cik_lookup=company,
            filing_type=FilingType.FILING_4,
            user_agent=user_agent,
            start_date=start_date,
            end_date=end_date
        )
        
        # Get filing URLs
        try:
            urls_dict = company_filings.get_urls()
            # The URLs are returned as a dict with company as key
            if isinstance(urls_dict, dict):
                # Get the URLs for the first (and likely only) key
                company_key = list(urls_dict.keys())[0] if urls_dict else None
                filing_urls = urls_dict.get(company_key, []) if company_key else []
            else:
                filing_urls = list(urls_dict) if urls_dict else []
        except Exception as e:
            logger.error(f"Error getting filing URLs: {e}")
            filing_urls = []
        
        # Deduplicate URLs
        filing_urls = list(dict.fromkeys(filing_urls))
        
        # Process each filing
        for filing_url in filing_urls[:50]:  # Limit to recent 50 filings
            try:
                # Extract accession number from URL
                accession = filing_url.split('/')[-2]
                
                # For Form 4, we need the primary document XML
                if not filing_url.endswith('.xml'):
                    # First, fetch the index to find the XML filename
                    index_content = parser.fetch_filing_content(filing_url)
                    if index_content and '<FILENAME>' in index_content:
                        # Look for XML filename in the index
                        import re
                        xml_match = re.search(r'<FILENAME>([^<]+\.xml)', index_content)
                        if xml_match:
                            xml_filename = xml_match.group(1)
                            base_url = filing_url.rsplit('/', 1)[0]
                            xml_url = f"{base_url}/{xml_filename}"
                        else:
                            # Default to doc1.xml if no match
                            base_url = filing_url.rsplit('/', 1)[0]
                            xml_url = f"{base_url}/doc1.xml"
                    else:
                        # Fallback
                        base_url = filing_url.rsplit('/', 1)[0]
                        xml_url = f"{base_url}/doc1.xml"
                else:
                    xml_url = filing_url
                
                # Fetch and parse filing
                xml_content = parser.fetch_filing_content(xml_url)
                if xml_content:
                    filing_transactions = parser.parse_form4_xml(xml_content, accession)
                    transactions.extend(filing_transactions)
            
            except Exception as e:
                logger.error(f"Error processing filing {filing_url}: {e}")
    
    except Exception as e:
        logger.error(f"Error getting recent insider activity: {e}")
    
    # Filter by minimum transaction value
    if min_transaction_value:
        transactions = [
            t for t in transactions 
            if t.total_value and t.total_value >= min_transaction_value
        ]
    
    # Sort by date
    transactions.sort(key=lambda x: x.transaction_date, reverse=True)
    
    # Group by insider
    insider_activity = {}
    for trans in transactions:
        if trans.insider_name not in insider_activity:
            insider_activity[trans.insider_name] = {
                "title": trans.insider_title,
                "transactions": [],
                "total_bought": 0,
                "total_sold": 0,
                "net_shares": 0
            }
        
        insider_activity[trans.insider_name]["transactions"].append(trans.to_dict())
        
        if trans.transaction_type.name in ["PURCHASE", "EXERCISE"]:
            insider_activity[trans.insider_name]["total_bought"] += trans.shares
            insider_activity[trans.insider_name]["net_shares"] += trans.shares
        elif trans.transaction_type.name == "SALE":
            insider_activity[trans.insider_name]["total_sold"] += trans.shares
            insider_activity[trans.insider_name]["net_shares"] -= trans.shares
    
    # Calculate overall statistics
    total_bought = sum(i["total_bought"] for i in insider_activity.values())
    total_sold = sum(i["total_sold"] for i in insider_activity.values())
    
    return {
        "company": company,
        "date_range": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "days": days_back
        },
        "transaction_count": len(transactions),
        "insider_count": len(insider_activity),
        "overall_activity": {
            "total_shares_bought": total_bought,
            "total_shares_sold": total_sold,
            "net_shares": total_bought - total_sold,
            "buy_sell_ratio": total_bought / total_sold if total_sold > 0 else float('inf')
        },
        "insiders": insider_activity,
        "recent_transactions": [t.to_dict() for t in transactions[:20]]  # Top 20 most recent
    }


def analyze_insider_patterns(
    company: str,
    time_period: str = "1Y",
    user_agent: str = None
) -> Dict[str, Any]:
    """Implementation of analyze_insider_patterns tool."""
    
    # Parse time period
    period_map = {
        "1M": 30,
        "3M": 90,
        "6M": 180,
        "1Y": 365,
        "2Y": 730,
        "5Y": 1825
    }
    
    days_back = period_map.get(time_period.upper(), 365)
    
    # Get recent activity
    activity = get_recent_insider_activity(
        company=company,
        days_back=days_back,
        user_agent=user_agent
    )
    
    # Analyze patterns
    patterns = {
        "time_period": time_period,
        "buy_sell_ratio": activity["overall_activity"]["buy_sell_ratio"],
        "net_insider_sentiment": "BULLISH" if activity["overall_activity"]["net_shares"] > 0 else "BEARISH",
        "most_active_insiders": [],
        "largest_transactions": [],
        "monthly_trends": {}
    }
    
    # Find most active insiders
    insider_list = [
        {
            "name": name,
            "title": data["title"],
            "transaction_count": len(data["transactions"]),
            "net_shares": data["net_shares"]
        }
        for name, data in activity["insiders"].items()
    ]
    
    patterns["most_active_insiders"] = sorted(
        insider_list,
        key=lambda x: x["transaction_count"],
        reverse=True
    )[:10]
    
    # Find largest transactions
    all_transactions = []
    for insider_data in activity["insiders"].values():
        all_transactions.extend(insider_data["transactions"])
    
    patterns["largest_transactions"] = sorted(
        all_transactions,
        key=lambda x: x.get("total_value", 0) or 0,
        reverse=True
    )[:10]
    
    return patterns


def calculate_insider_summary(transactions: List[InsiderTransaction]) -> Dict[str, Any]:
    """Calculate summary statistics for a list of insider transactions."""
    
    if not transactions:
        return {
            "total_transactions": 0,
            "total_shares_bought": 0,
            "total_shares_sold": 0,
            "total_value_bought": 0,
            "total_value_sold": 0,
            "net_shares": 0,
            "net_value": 0
        }
    
    bought_shares = sum(
        t.shares for t in transactions 
        if t.transaction_type.name in ["PURCHASE", "EXERCISE"]
    )
    sold_shares = sum(
        t.shares for t in transactions 
        if t.transaction_type.name == "SALE"
    )
    
    bought_value = sum(
        t.total_value or 0 for t in transactions 
        if t.transaction_type.name in ["PURCHASE", "EXERCISE"] and t.total_value
    )
    sold_value = sum(
        t.total_value or 0 for t in transactions 
        if t.transaction_type.name == "SALE" and t.total_value
    )
    
    return {
        "total_transactions": len(transactions),
        "total_shares_bought": bought_shares,
        "total_shares_sold": sold_shares,
        "total_value_bought": bought_value,
        "total_value_sold": sold_value,
        "net_shares": bought_shares - sold_shares,
        "net_value": bought_value - sold_value,
        "average_buy_price": bought_value / bought_shares if bought_shares > 0 else None,
        "average_sell_price": sold_value / sold_shares if sold_shares > 0 else None,
        "date_range": {
            "first": min(t.transaction_date for t in transactions).isoformat(),
            "last": max(t.transaction_date for t in transactions).isoformat()
        }
    }