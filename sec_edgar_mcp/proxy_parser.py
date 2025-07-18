"""Proxy statement (DEF 14A) parser for current board positions."""

import logging
import re
import requests
from typing import List, Dict, Any, Optional, Set
from datetime import date, datetime, timedelta
from dataclasses import dataclass
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from secedgar import filings, FilingType

from .models import BoardPosition, PositionType, PositionStatus
from .utils import rate_limited, cached, normalize_ticker, parse_date

logger = logging.getLogger(__name__)


@dataclass
class ProxyBoardMember:
    """Board member information extracted from proxy statements."""
    name: str
    position: str
    age: Optional[int]
    tenure_years: Optional[int]
    appointment_date: Optional[date]
    committees: List[str]
    compensation: Optional[float]
    independence: Optional[bool]
    other_directorships: List[str]
    
    
class ProxyStatementParser:
    """Parser for DEF 14A proxy statements to extract current board information."""
    
    def __init__(self, user_agent: str):
        self.user_agent = user_agent
        
    @rate_limited
    def fetch_filing_content(self, url: str) -> Optional[str]:
        """Fetch content from SEC filing URL."""
        try:
            headers = {'User-Agent': self.user_agent}
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Error fetching filing from {url}: {e}")
            return None
    
    def parse_proxy_statement(self, content: str, company_name: str, company_cik: str, 
                            ticker: str, accession_number: str) -> List[BoardPosition]:
        """
        Parse proxy statement to extract current board positions.
        
        Proxy statements (DEF 14A) contain the most accurate information about
        current board members, their positions, and appointment dates.
        """
        if not content:
            return []
        
        logger.info(f"Parsing proxy statement for {company_name} ({ticker})")
        
        try:
            # Clean and prepare content for parsing
            content_clean = self._clean_proxy_content(content)
            
            # Extract board member information
            board_members = self._extract_board_members(content_clean)
            
            # Convert to BoardPosition objects
            board_positions = []
            
            for member in board_members:
                position_type = self._classify_position_type(member.position)
                
                board_position = BoardPosition(
                    person_name=member.name,
                    person_cik=None,  # Usually not available in proxy statements
                    company_name=company_name,
                    company_cik=company_cik,
                    ticker=ticker,
                    position_type=position_type,
                    position_status=PositionStatus.CURRENT,  # Proxy statements show current positions
                    appointment_date=member.appointment_date,
                    resignation_date=None,  # Current positions don't have resignation dates
                    committees=member.committees,
                    compensation=member.compensation,
                    source_filing_type="DEF 14A",
                    source_accession=accession_number,
                    last_verified=datetime.now()
                )
                
                board_positions.append(board_position)
            
            logger.info(f"Extracted {len(board_positions)} board positions from proxy statement")
            return board_positions
            
        except Exception as e:
            logger.error(f"Error parsing proxy statement: {e}")
            return []
    
    def _clean_proxy_content(self, content: str) -> str:
        """Clean proxy statement content for easier parsing."""
        # Remove HTML tags if present
        if '<' in content and '>' in content:
            soup = BeautifulSoup(content, 'html.parser')
            content = soup.get_text()
        
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content)
        
        # Remove page numbers and headers/footers
        content = re.sub(r'Page \d+', '', content)
        content = re.sub(r'\d+\s*$', '', content, flags=re.MULTILINE)
        
        return content
    
    def _extract_board_members(self, content: str) -> List[ProxyBoardMember]:
        """Extract board member information from proxy statement content."""
        board_members = []
        
        # Common section headers for board information
        board_sections = [
            r'(?i)directors?\s+and\s+executive\s+officers?',
            r'(?i)board\s+of\s+directors?',
            r'(?i)director\s+nominees?',
            r'(?i)continuing\s+directors?',
            r'(?i)management\s+and\s+directors?'
        ]
        
        # Find board section
        board_content = None
        for pattern in board_sections:
            match = re.search(pattern, content)
            if match:
                start_pos = match.start()
                # Find end of section (next major heading or end of document)
                end_match = re.search(r'(?i)(compensation|audit|governance|proposal)', content[start_pos + 100:])
                if end_match:
                    end_pos = start_pos + 100 + end_match.start()
                    board_content = content[start_pos:end_pos]
                else:
                    board_content = content[start_pos:start_pos + 10000]  # Take next 10k chars
                break
        
        if not board_content:
            logger.warning("Could not find board section in proxy statement")
            return board_members
        
        # Extract individual director information
        # Look for patterns like "Name, Age X" or "Name (Age X)"
        director_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]*\.?)*(?:\s+[A-Z][a-z]+)+)(?:,?\s*(?:Age\s*)?(?:\(?)?\d{2,3}(?:\)?)?)?'
        
        potential_directors = re.finditer(director_pattern, board_content)
        
        for match in potential_directors:
            name = match.group(1).strip()
            age = int(match.group(2)) if match.group(2) else None
            
            # Skip if name is too short or contains common non-name words
            if len(name) < 6 or any(word in name.lower() for word in ['committee', 'board', 'director', 'officer']):
                continue
            
            # Extract additional information around this name
            start_pos = max(0, match.start() - 200)
            end_pos = min(len(board_content), match.end() + 500)
            context = board_content[start_pos:end_pos]
            
            # Extract position information
            position = self._extract_position_info(context, name)
            
            # Extract committee memberships
            committees = self._extract_committees(context)
            
            # Extract tenure/appointment date
            appointment_date, tenure_years = self._extract_tenure_info(context)
            
            # Extract compensation if available
            compensation = self._extract_compensation(context)
            
            member = ProxyBoardMember(
                name=name,
                position=position,
                age=age,
                tenure_years=tenure_years,
                appointment_date=appointment_date,
                committees=committees,
                compensation=compensation,
                independence=self._determine_independence(context),
                other_directorships=self._extract_other_directorships(context)
            )
            
            board_members.append(member)
        
        # Remove duplicates based on name similarity
        board_members = self._deduplicate_board_members(board_members)
        
        return board_members
    
    def _extract_position_info(self, context: str, name: str) -> str:
        """Extract position/title information for a board member."""
        # Look for position titles near the name
        position_patterns = [
            r'(?i)(chairman|chair|president|ceo|chief executive|cfo|chief financial|coo|chief operating)',
            r'(?i)(director|independent director|lead director|board member)',
            r'(?i)(vice chairman|vice president|executive vice president)'
        ]
        
        for pattern in position_patterns:
            match = re.search(pattern, context)
            if match:
                return match.group(1).title()
        
        return "Director"  # Default position
    
    def _extract_committees(self, context: str) -> List[str]:
        """Extract committee memberships from context."""
        committees = []
        
        committee_patterns = [
            r'(?i)(audit\s+committee)',
            r'(?i)(compensation\s+committee)',
            r'(?i)(nominating\s+committee)',
            r'(?i)(governance\s+committee)',
            r'(?i)(risk\s+committee)',
            r'(?i)(executive\s+committee)',
            r'(?i)(finance\s+committee)'
        ]
        
        for pattern in committee_patterns:
            match = re.search(pattern, context)
            if match:
                committees.append(match.group(1).title())
        
        return list(set(committees))  # Remove duplicates
    
    def _extract_tenure_info(self, context: str) -> tuple[Optional[date], Optional[int]]:
        """Extract tenure information and calculate appointment date."""
        # Look for tenure patterns like "Director since 2018" or "10 years"
        tenure_patterns = [
            r'(?i)(?:director\s+)?since\s+(\d{4})',
            r'(?i)(\d{1,2})\s+years?\s+(?:of\s+)?(?:service|tenure)',
            r'(?i)appointed\s+(?:in\s+)?(\d{4})'
        ]
        
        for pattern in tenure_patterns:
            match = re.search(pattern, context)
            if match:
                value = match.group(1)
                if len(value) == 4:  # Year format
                    year = int(value)
                    appointment_date = date(year, 1, 1)  # Approximate to beginning of year
                    tenure_years = date.today().year - year
                    return appointment_date, tenure_years
                else:  # Years format
                    tenure_years = int(value)
                    appointment_year = date.today().year - tenure_years
                    appointment_date = date(appointment_year, 1, 1)
                    return appointment_date, tenure_years
        
        return None, None
    
    def _extract_compensation(self, context: str) -> Optional[float]:
        """Extract compensation information if available."""
        # Look for dollar amounts that might be compensation
        compensation_pattern = r'\$([\\d,]+(?:\\.\\d{2})?)'
        
        matches = re.findall(compensation_pattern, context)
        if matches:
            # Take the largest amount found (likely total compensation)
            amounts = [float(m.replace(',', '')) for m in matches]
            return max(amounts)
        
        return None
    
    def _determine_independence(self, context: str) -> Optional[bool]:
        """Determine if director is independent based on context."""
        if re.search(r'(?i)independent\s+director', context):
            return True
        elif re.search(r'(?i)(?:employee|officer|management)', context):
            return False
        return None
    
    def _extract_other_directorships(self, context: str) -> List[str]:
        """Extract other public company directorships."""
        # This is complex and would require extensive pattern matching
        # For now, return empty list
        return []
    
    def _classify_position_type(self, position: str) -> PositionType:
        """Classify position string into PositionType enum."""
        position_lower = position.lower()
        
        if 'chairman' in position_lower:
            if 'vice' in position_lower:
                return PositionType.VICE_CHAIRMAN
            return PositionType.CHAIRMAN
        elif 'ceo' in position_lower or 'chief executive' in position_lower:
            return PositionType.CEO
        elif 'cfo' in position_lower or 'chief financial' in position_lower:
            return PositionType.CFO
        elif 'coo' in position_lower or 'chief operating' in position_lower:
            return PositionType.COO
        elif 'president' in position_lower:
            return PositionType.PRESIDENT
        elif 'lead director' in position_lower:
            return PositionType.LEAD_DIRECTOR
        elif 'independent director' in position_lower:
            return PositionType.INDEPENDENT_DIRECTOR
        elif 'director' in position_lower:
            return PositionType.DIRECTOR
        else:
            return PositionType.UNKNOWN
    
    def _deduplicate_board_members(self, members: List[ProxyBoardMember]) -> List[ProxyBoardMember]:
        """Remove duplicate board members based on name similarity."""
        unique_members = []
        seen_names = set()
        
        for member in members:
            # Normalize name for comparison
            normalized_name = member.name.lower().replace('.', '').replace(',', '').strip()
            
            if normalized_name not in seen_names:
                unique_members.append(member)
                seen_names.add(normalized_name)
        
        return unique_members


@cached(filing_type='proxy')
@rate_limited
def get_current_board_from_proxy(company: str, user_agent: str) -> List[BoardPosition]:
    """Get current board positions from most recent proxy statement."""
    
    parser = ProxyStatementParser(user_agent)
    
    try:
        # Get most recent DEF 14A filing
        end_date = date.today()
        start_date = end_date - timedelta(days=500)  # Look back 500 days for proxy
        
        company_filings = filings(
            cik_lookup=company,
            filing_type=FilingType.DEF14A,  # Proxy statements
            user_agent=user_agent,
            start_date=start_date,
            end_date=end_date
        )
        
        # Get filing URLs
        urls_dict = company_filings.get_urls()
        
        if isinstance(urls_dict, dict):
            company_key = list(urls_dict.keys())[0] if urls_dict else None
            filing_urls = urls_dict.get(company_key, []) if company_key else []
        else:
            filing_urls = list(urls_dict) if urls_dict else []
        
        if not filing_urls:
            logger.warning(f"No proxy statements found for {company}")
            return []
        
        # Use most recent proxy statement
        latest_filing_url = filing_urls[0]
        
        logger.info(f"Processing proxy statement: {latest_filing_url}")
        
        # Fetch and parse the proxy statement
        content = parser.fetch_filing_content(latest_filing_url)
        
        if content:
            # Extract accession number from URL
            accession = latest_filing_url.split('/')[-2] if '/' in latest_filing_url else 'unknown'
            
            # Parse the proxy statement
            board_positions = parser.parse_proxy_statement(
                content=content,
                company_name=company,  # Will be enhanced with actual company name
                company_cik=company,   # Will be enhanced with actual CIK
                ticker=company,
                accession_number=accession
            )
            
            return board_positions
        
        return []
        
    except Exception as e:
        logger.error(f"Error getting board positions from proxy for {company}: {e}")
        return []