"""Person to CIK resolver for more efficient SEC searches."""

import logging
import re
import json
from typing import Optional, Dict, List, Any
from datetime import date, timedelta
import requests

from .utils import rate_limited, cached
from .sec_fulltext_search import SECFullTextSearcher, generate_name_variations
from .name_matching import name_matcher

logger = logging.getLogger(__name__)


class PersonCIKResolver:
    """
    Resolves person names to their SEC CIK (Central Index Key) numbers.
    
    This enables more efficient searches as we can directly query by CIK
    rather than searching by name across multiple variations.
    """
    
    def __init__(self, user_agent: str):
        self.user_agent = user_agent
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': user_agent})
        self.fulltext_searcher = SECFullTextSearcher(user_agent)
        
        # In-memory cache for resolved CIKs
        self._cik_cache = {}
    
    @cached(filing_type='person_cik')
    def resolve_person_cik(self, person_name: str) -> Optional[Dict[str, Any]]:
        """
        Resolve a person's name to their CIK and associated metadata.
        
        Returns:
            Dictionary with CIK and metadata, or None if not found
            {
                'cik': '0001234567',
                'name': 'KLAPPA GALE E',
                'name_variations': ['Gale Klappa', 'KLAPPA GALE E'],
                'companies': ['WEC', 'ASB', 'BMI'],
                'confidence': 0.95
            }
        """
        # Check cache first
        cache_key = person_name.upper().strip()
        if cache_key in self._cik_cache:
            return self._cik_cache[cache_key]
        
        logger.info(f"Attempting to resolve CIK for: {person_name}")
        
        # Try multiple methods to find the CIK
        result = None
        
        # Method 1: Extract from recent Form 4 filings
        result = self._extract_cik_from_form4s(person_name)
        
        # Method 2: Use SEC's entity search (if available)
        if not result:
            result = self._search_sec_entities(person_name)
        
        # Method 3: Parse from known filing URLs
        if not result:
            result = self._extract_from_filing_urls(person_name)
        
        if result:
            self._cik_cache[cache_key] = result
            logger.info(f"Successfully resolved CIK for {person_name}: {result['cik']}")
        else:
            logger.warning(f"Could not resolve CIK for {person_name}")
        
        return result
    
    def _extract_cik_from_form4s(self, person_name: str) -> Optional[Dict[str, Any]]:
        """Extract CIK from recent Form 4 filings."""
        try:
            # Get recent Form 4s
            recent_filings = self.fulltext_searcher.search_form4_by_person(
                person_name=person_name,
                start_date=date.today() - timedelta(days=365),
                limit=10
            )
            
            if not recent_filings:
                return None
            
            cik_candidates = {}
            name_variations_found = set()
            companies = set()
            
            for filing in recent_filings:
                if not filing.get('filing_url'):
                    continue
                
                try:
                    # Fetch filing content
                    response = self.session.get(filing['filing_url'])
                    response.raise_for_status()
                    content = response.text
                    
                    # Extract reporting owner CIK
                    # Look for patterns like:
                    # <reportingOwnerId>
                    #   <rptOwnerCik>0001234567</rptOwnerCik>
                    #   <rptOwnerName>KLAPPA GALE E</rptOwnerName>
                    
                    # Find all reporting owners
                    owner_pattern = re.compile(
                        r'<reportingOwnerId>.*?<rptOwnerCik>(\d{10})</rptOwnerCik>.*?<rptOwnerName>([^<]+)</rptOwnerName>.*?</reportingOwnerId>',
                        re.DOTALL | re.IGNORECASE
                    )
                    
                    for match in owner_pattern.finditer(content):
                        cik = match.group(1)
                        name = match.group(2).strip()
                        
                        # Check if this name matches our search
                        if self._is_name_match(person_name, name):
                            if cik not in cik_candidates:
                                cik_candidates[cik] = {
                                    'count': 0,
                                    'names': set()
                                }
                            cik_candidates[cik]['count'] += 1
                            cik_candidates[cik]['names'].add(name)
                            name_variations_found.add(name)
                            
                            # Track companies
                            if filing.get('ticker'):
                                companies.add(filing['ticker'])
                    
                except Exception as e:
                    logger.debug(f"Error parsing filing: {e}")
                    continue
            
            # Select the most common CIK
            if cik_candidates:
                best_cik = max(cik_candidates.items(), key=lambda x: x[1]['count'])
                
                return {
                    'cik': best_cik[0],
                    'name': list(best_cik[1]['names'])[0],  # Use most common name form
                    'name_variations': list(name_variations_found),
                    'companies': list(companies),
                    'confidence': min(0.95, 0.7 + (best_cik[1]['count'] * 0.05))  # Higher count = higher confidence
                }
        
        except Exception as e:
            logger.error(f"Error extracting CIK from Form 4s: {e}")
        
        return None
    
    def _search_sec_entities(self, person_name: str) -> Optional[Dict[str, Any]]:
        """
        Search SEC's entity database for the person.
        
        Note: This would require access to SEC's entity search API
        which may not be publicly documented.
        """
        # This is a placeholder for potential future implementation
        # The SEC does have entity search but it's not well documented
        return None
    
    def _extract_from_filing_urls(self, person_name: str) -> Optional[Dict[str, Any]]:
        """
        Try to extract CIK from filing URLs if we have them cached.
        
        Filing URLs often contain the CIK in the path.
        """
        # This would check our cache or database for known filing URLs
        # associated with this person
        return None
    
    def _is_name_match(self, search_name: str, found_name: str) -> bool:
        """
        Check if two names match, accounting for variations.
        
        Examples:
            "Gale Klappa" matches "KLAPPA GALE E"
            "John Smith" matches "Smith, John"
        """
        # Normalize names
        search_clean = re.sub(r'[^\w\s]', '', search_name.upper()).split()
        found_clean = re.sub(r'[^\w\s]', '', found_name.upper()).split()
        
        # Check if all parts of search name are in found name
        search_set = set(search_clean)
        found_set = set(found_clean)
        
        # If all search parts are in found parts, it's a match
        if search_set.issubset(found_set):
            return True
        
        # Check for last name, first name pattern
        if len(search_clean) >= 2 and len(found_clean) >= 2:
            # "First Last" vs "Last First"
            if (search_clean[0] == found_clean[1] and search_clean[1] == found_clean[0]) or \
               (search_clean[0] == found_clean[0] and search_clean[-1] == found_clean[-1]):
                return True
        
        return False
    
    @rate_limited
    def search_by_cik(self, cik: str, form_type: str = "4") -> List[Dict[str, Any]]:
        """
        Search for all filings by a specific CIK.
        
        This is more efficient than searching by name.
        """
        try:
            # SEC submissions endpoint for a specific CIK
            url = f"https://data.sec.gov/submissions/CIK{cik}.json"
            
            response = self.session.get(url)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract recent filings
            recent_filings = []
            filings = data.get('filings', {}).get('recent', {})
            
            if filings:
                forms = filings.get('form', [])
                dates = filings.get('filingDate', [])
                accessions = filings.get('accessionNumber', [])
                primary_docs = filings.get('primaryDocument', [])
                
                for i in range(len(forms)):
                    if forms[i] == form_type:
                        recent_filings.append({
                            'form_type': forms[i],
                            'filing_date': dates[i] if i < len(dates) else None,
                            'accession_number': accessions[i] if i < len(accessions) else None,
                            'document': primary_docs[i] if i < len(primary_docs) else None,
                            'cik': cik
                        })
            
            return recent_filings[:100]  # Limit to most recent 100
            
        except Exception as e:
            logger.error(f"Error searching by CIK {cik}: {e}")
            return []


def integrate_cik_resolver(mcp, user_agent: str):
    """Register CIK resolver tools with the MCP server."""
    
    resolver = PersonCIKResolver(user_agent)
    
    @mcp.tool("resolve_person_cik")
    def resolve_person_cik_tool(person_name: str) -> Dict[str, Any]:
        """
        Resolve a person's name to their SEC CIK number.
        
        The CIK (Central Index Key) is a unique identifier assigned by the SEC
        to individuals and companies who file reports.
        
        Parameters:
            person_name: Full name of the person
            
        Returns:
            Dictionary with CIK and metadata, or error if not found
            
        Example:
            resolve_person_cik("Gale Klappa")
        """
        result = resolver.resolve_person_cik(person_name)
        
        if result:
            return {
                "success": True,
                "person_name": person_name,
                "cik": result['cik'],
                "canonical_name": result['name'],
                "name_variations": result['name_variations'],
                "known_companies": result['companies'],
                "confidence_score": result['confidence']
            }
        else:
            return {
                "success": False,
                "person_name": person_name,
                "error": "Could not resolve CIK for this person",
                "suggestion": "Try searching with different name variations or check if the person has recent SEC filings"
            }