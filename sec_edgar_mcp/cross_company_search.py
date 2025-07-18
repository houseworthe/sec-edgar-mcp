"""Cross-company insider search capabilities for SEC EDGAR MCP."""

import logging
import requests
from typing import List, Dict, Any, Optional, Set
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from mcp.server.fastmcp import FastMCP

from .insider_tools import get_insider_transactions
from .models import InsiderTransaction
from .utils import rate_limited, cached, normalize_ticker, parse_date
from .name_matching import enhance_name_matching_in_search, name_matcher
from .sec_fulltext_search import SECFullTextSearcher, generate_name_variations

logger = logging.getLogger(__name__)


@dataclass
class CompanyInsiderSummary:
    """Summary of insider activity at a specific company."""
    ticker: str
    company_name: str
    cik: Optional[str]
    transaction_count: int
    total_shares_bought: float
    total_shares_sold: float
    net_shares: float
    first_transaction_date: Optional[date]
    last_transaction_date: Optional[date]
    current_position: Optional[str]
    position_status: str  # "current", "former", "unknown"


@dataclass
class CrossCompanyInsiderProfile:
    """Complete insider profile across all companies."""
    person_name: str
    total_companies: int
    active_positions: int
    former_positions: int
    companies: List[CompanyInsiderSummary]
    total_transactions: int
    search_date: date


def register_cross_company_tools(mcp: FastMCP, user_agent: str):
    """Register cross-company search tools with the MCP server."""
    
    @mcp.tool("get_all_insider_companies")
    def get_all_insider_companies_tool(
        person_name: str,
        include_former: bool = True,
        min_transactions: int = 1,
        years_back: int = 10,
        user_agent: str = user_agent
    ) -> Dict[str, Any]:
        """
        Find ALL companies where a person is or was an insider.
        
        This is the solution to the cross-company search limitation.
        Searches across all public companies to find insider activity.
        
        Parameters:
            person_name: Full name of the person to search for
            include_former: Include companies where person was formerly an insider
            min_transactions: Minimum number of transactions to consider significant
            years_back: How many years to search back (default: 10)
            user_agent: User agent string required by the SEC
            
        Returns:
            Dictionary containing complete insider profile across all companies
            
        Example:
            get_all_insider_companies("Gale Klappa", include_former=True)
        """
        return get_all_insider_companies(
            person_name=person_name,
            include_former=include_former,
            min_transactions=min_transactions,
            years_back=years_back,
            user_agent=user_agent
        )
    
    @mcp.tool("get_current_board_positions")
    def get_current_board_positions_tool(
        person_name: str,
        user_agent: str = user_agent
    ) -> Dict[str, Any]:
        """
        Get only current active board positions for a person.
        
        Filters out former positions and focuses on current roles.
        
        Parameters:
            person_name: Full name of the person
            user_agent: User agent string required by the SEC
            
        Returns:
            Dictionary containing only current/active board positions
            
        Example:
            get_current_board_positions("Gale Klappa")
        """
        return get_current_board_positions(
            person_name=person_name,
            user_agent=user_agent
        )


@cached(filing_type='cross_company')
@rate_limited
def get_all_insider_companies(
    person_name: str,
    include_former: bool = True,
    min_transactions: int = 1,
    years_back: int = 10,
    user_agent: str = None,
    use_fulltext_search: bool = True,
    company_limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Implementation of cross-company insider search.
    
    This addresses the core limitation where searches required company parameter.
    Now searches across ALL companies to find insider activity.
    
    Parameters:
        person_name: Name of the person to search for
        include_former: Include companies where person was formerly an insider
        min_transactions: Minimum number of transactions to consider significant
        years_back: How many years to search back
        user_agent: User agent string required by the SEC
        use_fulltext_search: Use SEC full-text search (recommended) vs brute force
        company_limit: Limit number of companies to search (None = all companies)
    """
    
    logger.info(f"Starting cross-company search for {person_name} (method: {'fulltext' if use_fulltext_search else 'brute-force'})")
    
    # Calculate date range
    end_date = date.today()
    start_date = end_date - timedelta(days=years_back * 365)
    
    # Use full-text search method (RECOMMENDED)
    if use_fulltext_search:
        try:
            searcher = SECFullTextSearcher(user_agent)
            
            # Get companies where this person has filed Form 4s
            companies_from_search = searcher.get_companies_for_person(person_name)
            
            logger.info(f"Full-text search found {len(companies_from_search)} companies for {person_name}")
            
            # Convert to our format and get detailed transaction data
            companies_with_activity = []
            
            for company_info in companies_from_search:
                ticker = company_info.get('ticker')
                if not ticker:
                    continue
                
                try:
                    # Get detailed transactions for this company
                    result = get_insider_transactions(
                        person_name=person_name,
                        company=ticker,
                        start_date=start_date.isoformat(),
                        end_date=end_date.isoformat(),
                        user_agent=user_agent
                    )
                    
                    if result and result.get('transaction_count', 0) >= min_transactions:
                        summary = result.get('summary', {})
                        transactions = result.get('transactions', [])
                        
                        # Determine position status
                        position_status = determine_position_status(transactions, end_date)
                        current_position = extract_current_position(transactions)
                        
                        companies_with_activity.append(CompanyInsiderSummary(
                            ticker=ticker,
                            company_name=company_info.get('company_name', ''),
                            cik=company_info.get('cik'),
                            transaction_count=result['transaction_count'],
                            total_shares_bought=summary.get('total_shares_bought', 0),
                            total_shares_sold=summary.get('total_shares_sold', 0),
                            net_shares=summary.get('net_shares', 0),
                            first_transaction_date=parse_date(summary.get('date_range', {}).get('first')) if summary.get('date_range') else None,
                            last_transaction_date=parse_date(summary.get('date_range', {}).get('last')) if summary.get('date_range') else None,
                            current_position=current_position,
                            position_status=position_status
                        ))
                        
                except Exception as e:
                    logger.warning(f"Error getting detailed transactions for {ticker}: {e}")
                    # Still include basic info if we have it
                    if company_info.get('filing_count', 0) >= min_transactions:
                        companies_with_activity.append(CompanyInsiderSummary(
                            ticker=ticker,
                            company_name=company_info.get('company_name', ''),
                            cik=company_info.get('cik'),
                            transaction_count=company_info.get('filing_count', 0),
                            total_shares_bought=0,
                            total_shares_sold=0,
                            net_shares=0,
                            first_transaction_date=parse_date(company_info.get('first_filing')),
                            last_transaction_date=parse_date(company_info.get('last_filing')),
                            current_position='Unknown',
                            position_status='unknown'
                        ))
                    continue
            
        except Exception as e:
            logger.error(f"Full-text search failed: {str(e)}")
            logger.info("Falling back to brute-force search method")
            use_fulltext_search = False
            companies_with_activity = []  # Reset in case of partial results
    
    # Fallback to brute-force method if full-text search fails or is disabled
    if not use_fulltext_search:
        # Get list of all public companies
        company_list = get_all_public_companies(user_agent)
        
        if not company_list:
            logger.error("Could not retrieve company list")
            return {
                "person_name": person_name,
                "error": "Could not retrieve public company listings",
                "companies": [],
                "total_companies": 0
            }
        
        # Apply company limit if specified
        if company_limit:
            company_list = company_list[:company_limit]
            logger.info(f"Searching across {len(company_list)} companies (limited from {len(get_all_public_companies(user_agent))})")
        else:
            logger.info(f"Searching across ALL {len(company_list)} public companies")
        
        # Search for insider activity across companies
        companies_with_activity = []
        
        # Use threading for faster searches, but respect rate limits
        def search_company(company_info):
            """Search a single company for insider activity."""
            ticker = company_info.get('ticker', '').strip()
            company_name = company_info.get('title', '').strip()
            cik = company_info.get('cik_str', '').strip()
            
            if not ticker:
                return None
                
            try:
                # Search for insider transactions at this company
                result = get_insider_transactions(
                    person_name=person_name,
                    company=ticker,
                    start_date=start_date.isoformat(),
                    end_date=end_date.isoformat(),
                    user_agent=user_agent
                )
                
                if result and result.get('transaction_count', 0) >= min_transactions:
                    summary = result.get('summary', {})
                    transactions = result.get('transactions', [])
                    
                    # Determine position status
                    position_status = determine_position_status(transactions, end_date)
                    current_position = extract_current_position(transactions)
                    
                    return CompanyInsiderSummary(
                        ticker=ticker,
                        company_name=company_name,
                        cik=cik,
                        transaction_count=result['transaction_count'],
                        total_shares_bought=summary.get('total_shares_bought', 0),
                        total_shares_sold=summary.get('total_shares_sold', 0),
                        net_shares=summary.get('net_shares', 0),
                        first_transaction_date=parse_date(summary.get('date_range', {}).get('first')) if summary.get('date_range') else None,
                        last_transaction_date=parse_date(summary.get('date_range', {}).get('last')) if summary.get('date_range') else None,
                        current_position=current_position,
                        position_status=position_status
                    )
                    
            except Exception as e:
                logger.debug(f"Error searching {ticker}: {e}")
                return None
            
            return None
        
        # Execute searches with threading (but limited concurrency for rate limiting)
        max_workers = 5  # Conservative to respect SEC rate limits
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit searches for all companies
            future_to_company = {
                executor.submit(search_company, company): company 
                for company in company_list
            }
            
            # Add progress tracking
            completed = 0
            total = len(future_to_company)
            
            for future in as_completed(future_to_company):
                completed += 1
                if completed % 100 == 0:
                    logger.info(f"Progress: {completed}/{total} companies searched")
                
                try:
                    result = future.result()
                    if result:
                        companies_with_activity.append(result)
                        logger.info(f"Found insider activity: {result.ticker} - {result.transaction_count} transactions")
                except Exception as e:
                    logger.error(f"Error processing future: {e}")
    
    # Filter by include_former preference
    if not include_former:
        companies_with_activity = [
            c for c in companies_with_activity 
            if c.position_status in ["current", "unknown"]
        ]
    
    # Sort by most recent activity
    companies_with_activity.sort(
        key=lambda x: x.last_transaction_date or date.min, 
        reverse=True
    )
    
    # Calculate summary statistics
    active_positions = len([c for c in companies_with_activity if c.position_status == "current"])
    former_positions = len([c for c in companies_with_activity if c.position_status == "former"])
    total_transactions = sum(c.transaction_count for c in companies_with_activity)
    
    profile = CrossCompanyInsiderProfile(
        person_name=person_name,
        total_companies=len(companies_with_activity),
        active_positions=active_positions,
        former_positions=former_positions,
        companies=companies_with_activity,
        total_transactions=total_transactions,
        search_date=date.today()
    )
    
    logger.info(f"Cross-company search complete: {profile.total_companies} companies found")
    
    result = {
        "person_name": profile.person_name,
        "search_date": profile.search_date.isoformat(),
        "search_method": "fulltext" if use_fulltext_search else "brute-force",
        "summary": {
            "total_companies": profile.total_companies,
            "active_positions": profile.active_positions,
            "former_positions": profile.former_positions,
            "total_transactions": profile.total_transactions
        },
        "companies": [
            {
                "ticker": c.ticker,
                "company_name": c.company_name,
                "cik": c.cik,
                "position_status": c.position_status,
                "current_position": c.current_position,
                "transaction_summary": {
                    "total_transactions": c.transaction_count,
                    "shares_bought": c.total_shares_bought,
                    "shares_sold": c.total_shares_sold,
                    "net_shares": c.net_shares,
                    "first_transaction": c.first_transaction_date.isoformat() if c.first_transaction_date else None,
                    "last_transaction": c.last_transaction_date.isoformat() if c.last_transaction_date else None
                }
            }
            for c in companies_with_activity
        ]
    }
    
    # Add helpful message if no companies found
    if profile.total_companies == 0:
        result["message"] = (
            f"No insider activity found for '{person_name}'. "
            "This could mean: "
            "1) The person has not filed Form 4s with the SEC, "
            "2) The name format doesn't match SEC records (try variations like 'LAST, FIRST' or 'LAST FIRST MIDDLE'), "
            "3) The person may not be a public company insider. "
            f"Search method used: {result['search_method']}"
        )
        
        # Add name variations tried
        result["name_variations_searched"] = generate_name_variations(person_name)[:5]
    
    return result


def get_current_board_positions(person_name: str, user_agent: str = None) -> Dict[str, Any]:
    """Get only current active board positions."""
    
    # Get all companies first
    all_companies_result = get_all_insider_companies(
        person_name=person_name,
        include_former=False,  # Only current
        user_agent=user_agent
    )
    
    current_positions = [
        company for company in all_companies_result.get('companies', [])
        if company.get('position_status') == 'current'
    ]
    
    return {
        "person_name": person_name,
        "search_date": date.today().isoformat(),
        "current_positions_count": len(current_positions),
        "current_positions": current_positions
    }


@cached(filing_type='company_list')
def get_all_public_companies(user_agent: str) -> List[Dict[str, Any]]:
    """
    Get list of all public companies from SEC.
    
    Uses the SEC's company tickers endpoint to get comprehensive list.
    """
    try:
        url = "https://www.sec.gov/files/company_tickers.json"
        headers = {'User-Agent': user_agent}
        
        logger.info("Fetching complete list of public companies from SEC")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        
        # Convert to list format
        companies = []
        for key, company_info in data.items():
            if isinstance(company_info, dict):
                companies.append(company_info)
        
        logger.info(f"Retrieved {len(companies)} public companies")
        return companies
        
    except Exception as e:
        logger.error(f"Error fetching public companies list: {e}")
        return []


def determine_position_status(transactions: List[Dict], current_date: date) -> str:
    """
    Determine if insider position is current or former based on transaction patterns.
    
    Logic:
    - If transactions within last 12 months: likely current
    - If no transactions in 2+ years: likely former
    - Otherwise: unknown
    """
    if not transactions:
        return "unknown"
    
    try:
        # Get most recent transaction date
        latest_transaction = max(
            parse_date(t.get('transaction_date', '')) 
            for t in transactions 
            if t.get('transaction_date')
        )
        
        days_since_last = (current_date - latest_transaction).days
        
        if days_since_last <= 365:  # Within last year
            return "current"
        elif days_since_last >= 730:  # 2+ years ago
            return "former"
        else:
            return "unknown"
            
    except Exception as e:
        logger.debug(f"Error determining position status: {e}")
        return "unknown"


def extract_current_position(transactions: List[Dict]) -> Optional[str]:
    """Extract the person's current/most recent position title from transactions."""
    if not transactions:
        return None
    
    try:
        # Get most recent transaction and extract title
        latest_transaction = max(
            transactions,
            key=lambda t: parse_date(t.get('transaction_date', '')) or date.min
        )
        
        return latest_transaction.get('insider_title', 'Director')
        
    except Exception as e:
        logger.debug(f"Error extracting position: {e}")
        return None