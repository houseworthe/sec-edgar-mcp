"""SEC Full-Text Search Integration for cross-company insider searches."""

import logging
import requests
import re
from typing import List, Dict, Any, Optional, Set
from datetime import date, datetime, timedelta
import time
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
import json

from .utils import rate_limited, cached
from .models import Filing
from .name_matching import name_matcher

logger = logging.getLogger(__name__)


class SECFullTextSearcher:
    """
    Implements full-text search using SEC EDGAR's search capabilities.
    This allows searching for insiders across ALL companies efficiently.
    """
    
    BASE_URL = "https://www.sec.gov/edgar/search/"
    API_URL = "https://www.sec.gov/edgar/search-index"
    
    def __init__(self, user_agent: str):
        self.user_agent = user_agent
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': user_agent})
    
    @rate_limited
    def search_form4_by_person(
        self, 
        person_name: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 200
    ) -> List[Dict[str, Any]]:
        """
        Search for all Form 4 filings by a specific person across all companies.
        
        Parameters:
            person_name: Name of the person to search for
            start_date: Start date for search (default: 5 years ago)
            end_date: End date for search (default: today)
            limit: Maximum number of results to return
            
        Returns:
            List of Form 4 filing metadata including company info
        """
        if not start_date:
            start_date = date.today() - timedelta(days=5*365)
        if not end_date:
            end_date = date.today()
        
        # Generate name variations for better matching
        name_variations = generate_name_variations(person_name)
        
        all_results = []
        seen_accession_numbers = set()
        
        for name_variant in name_variations[:3]:  # Try top 3 variations
            try:
                results = self._perform_search(
                    query=name_variant,
                    form_type="4",
                    start_date=start_date,
                    end_date=end_date,
                    limit=limit
                )
                
                # Deduplicate results
                for result in results:
                    accession = result.get('accession_number')
                    if accession and accession not in seen_accession_numbers:
                        seen_accession_numbers.add(accession)
                        all_results.append(result)
                
            except Exception as e:
                logger.error(f"Error searching for name variant '{name_variant}': {e}")
                continue
        
        # Sort by date (most recent first)
        all_results.sort(key=lambda x: x.get('filing_date', ''), reverse=True)
        
        return all_results[:limit]
    
    def _perform_search(
        self,
        query: str,
        form_type: str = "4",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Perform the actual search using SEC's search API.
        
        This uses the JSON API endpoint that powers the SEC's search interface.
        """
        # Build search parameters
        params = {
            'q': f'"{query}"',  # Exact phrase search
            'dateRange': 'custom',
            'category': 'form-cat1',  # Company filings
            'forms': form_type,
            'startdt': start_date.strftime('%Y-%m-%d') if start_date else '',
            'enddt': end_date.strftime('%Y-%m-%d') if end_date else '',
            'from': 0,
            'size': min(limit, 100)  # SEC limits to 100 per request
        }
        
        try:
            # Make the search request
            response = self.session.post(
                self.API_URL,
                json=params,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Extract results
            results = []
            hits = data.get('hits', {}).get('hits', [])
            
            for hit in hits:
                source = hit.get('_source', {})
                
                # Extract company and filing info
                result = {
                    'accession_number': source.get('adsh'),
                    'filing_date': source.get('file_date'),
                    'form_type': source.get('form'),
                    'company_name': source.get('entity'),
                    'cik': source.get('ciks', [None])[0] if source.get('ciks') else None,
                    'ticker': self._extract_ticker_from_entity(source.get('entity', '')),
                    'filing_url': f"https://www.sec.gov/Archives/edgar/data/{source.get('ciks', [None])[0]}/{source.get('adsh', '').replace('-', '')}/{source.get('adsh')}.txt",
                    'reporting_owner': query,  # We searched for this person
                    'score': hit.get('_score', 0)
                }
                
                results.append(result)
            
            return results
            
        except requests.exceptions.RequestException as e:
            logger.error(f"SEC search request failed: {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse SEC search response: {e}")
            return []
    
    def _extract_ticker_from_entity(self, entity_string: str) -> Optional[str]:
        """
        Extract ticker symbol from entity string.
        SEC often includes ticker in parentheses: "Company Name (TICK)"
        """
        match = re.search(r'\(([A-Z]{1,5})\)$', entity_string)
        return match.group(1) if match else None
    
    @cached(filing_type='person_cik_lookup')
    def find_person_cik(self, person_name: str) -> Optional[str]:
        """
        Try to find a person's CIK by searching their recent filings.
        
        The CIK is often included in Form 4 filings and can be used
        for more efficient searches.
        """
        # Search for recent Form 4s by this person
        recent_filings = self.search_form4_by_person(
            person_name=person_name,
            start_date=date.today() - timedelta(days=365),
            limit=10
        )
        
        if not recent_filings:
            return None
        
        # Try to extract CIK from filing details
        for filing in recent_filings:
            try:
                # Fetch the filing content
                response = self.session.get(filing['filing_url'])
                response.raise_for_status()
                
                # Look for reporting owner CIK in the filing
                # Pattern: <reportingOwnerCik>0001234567</reportingOwnerCik>
                cik_match = re.search(
                    r'<reportingOwnerCik>(\d{10})</reportingOwnerCik>',
                    response.text,
                    re.IGNORECASE
                )
                
                if cik_match:
                    return cik_match.group(1)
                
            except Exception as e:
                logger.debug(f"Error extracting CIK from filing: {e}")
                continue
        
        return None
    
    def get_companies_for_person(self, person_name: str) -> List[Dict[str, Any]]:
        """
        Get a unique list of companies where a person has filed Form 4s.
        
        This is the main entry point for cross-company searches.
        """
        # Search for all Form 4s by this person
        filings = self.search_form4_by_person(
            person_name=person_name,
            start_date=date.today() - timedelta(days=10*365),  # 10 years
            limit=500  # Get more results for comprehensive view
        )
        
        # Group by company
        companies_map = {}
        
        for filing in filings:
            ticker = filing.get('ticker') or filing.get('cik', 'Unknown')
            company_name = filing.get('company_name', 'Unknown Company')
            
            if ticker not in companies_map:
                companies_map[ticker] = {
                    'ticker': ticker,
                    'company_name': company_name,
                    'cik': filing.get('cik'),
                    'filing_count': 0,
                    'first_filing': filing.get('filing_date'),
                    'last_filing': filing.get('filing_date'),
                    'filings': []
                }
            
            companies_map[ticker]['filing_count'] += 1
            companies_map[ticker]['filings'].append(filing)
            
            # Update date range
            filing_date = filing.get('filing_date')
            if filing_date:
                if filing_date < companies_map[ticker]['first_filing']:
                    companies_map[ticker]['first_filing'] = filing_date
                if filing_date > companies_map[ticker]['last_filing']:
                    companies_map[ticker]['last_filing'] = filing_date
        
        # Convert to list and sort by most recent activity
        companies = list(companies_map.values())
        companies.sort(key=lambda x: x['last_filing'], reverse=True)
        
        return companies


def generate_name_variations(person_name: str) -> List[str]:
    """
    Generate common variations of a person's name for search.
    
    Uses the intelligent name matcher to create variations.
    
    Examples:
        "John Smith" -> ["John Smith", "Smith John", "SMITH JOHN", "John Q Smith"]
    """
    variations = []
    
    # Clean and normalize the name
    normalized = name_matcher.normalize_name(person_name)
    parts = normalized.split()
    
    if not parts:
        return [person_name]
    
    # Original name
    variations.append(person_name)
    variations.append(normalized)
    
    # First Last
    if len(parts) >= 2:
        first_name = parts[0]
        last_name = parts[-1]
        
        # Common variations
        variations.extend([
            f"{first_name} {last_name}",
            f"{last_name} {first_name}",
            f"{last_name}, {first_name}",
            f"{last_name.upper()} {first_name.upper()}",
            f"{last_name.upper()}, {first_name.upper()}",
            # SEC format: LAST FIRST MIDDLE
            f"{last_name.upper()} {' '.join(p.upper() for p in parts[:-1])}"
        ])
    
    # Include middle initial variations if 3 parts
    if len(parts) == 3:
        first_name = parts[0]
        middle = parts[1]
        last_name = parts[2]
        
        variations.extend([
            f"{first_name} {middle[0]}. {last_name}",
            f"{first_name} {middle[0]} {last_name}",
            f"{last_name} {first_name} {middle[0]}",
            f"{last_name.upper()} {first_name.upper()} {middle[0].upper()}"
        ])
    
    # Remove duplicates while preserving order
    seen = set()
    unique_variations = []
    for v in variations:
        v_clean = v.strip()
        if v_clean and v_clean not in seen:
            seen.add(v_clean)
            unique_variations.append(v_clean)
    
    return unique_variations