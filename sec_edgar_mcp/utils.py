"""Utility functions for SEC EDGAR MCP server."""

import time
import functools
import hashlib
import json
import logging
from datetime import datetime, timedelta, date
from typing import Any, Dict, Optional, Callable, Union
from urllib.parse import urljoin
import re

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter for SEC API requests (10 requests per second max)."""
    
    def __init__(self, max_requests: int = 10, time_window: float = 1.0):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
    
    def wait_if_needed(self):
        """Wait if necessary to respect rate limits."""
        now = time.time()
        # Remove old requests outside the time window
        self.requests = [req_time for req_time in self.requests 
                        if now - req_time < self.time_window]
        
        if len(self.requests) >= self.max_requests:
            # Calculate wait time
            oldest_request = self.requests[0]
            wait_time = self.time_window - (now - oldest_request) + 0.1
            if wait_time > 0:
                logger.info(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)
        
        self.requests.append(now)


# Global rate limiter instance
rate_limiter = RateLimiter()


def rate_limited(func: Callable) -> Callable:
    """Decorator to apply rate limiting to functions."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        rate_limiter.wait_if_needed()
        return func(*args, **kwargs)
    return wrapper


class Cache:
    """Simple in-memory cache with TTL support."""
    
    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = {
            'form4': timedelta(hours=1),  # Form 4s are time-sensitive
            '13f': timedelta(days=1),     # 13Fs are quarterly
            '10k': timedelta(days=7),     # 10-Ks are annual
            '10q': timedelta(days=7),     # 10-Qs are quarterly
            '8k': timedelta(hours=1),     # 8-Ks are time-sensitive
            'default': timedelta(hours=4)
        }
    
    def _get_cache_key(self, key_parts: list) -> str:
        """Generate cache key from parts."""
        key_str = json.dumps(key_parts, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, key_parts: list, filing_type: str = 'default') -> Optional[Any]:
        """Get value from cache if not expired."""
        cache_key = self._get_cache_key(key_parts)
        
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if datetime.now() < entry['expires_at']:
                logger.debug(f"Cache hit for {cache_key}")
                return entry['value']
            else:
                # Remove expired entry
                del self.cache[cache_key]
                logger.debug(f"Cache expired for {cache_key}")
        
        return None
    
    def set(self, key_parts: list, value: Any, filing_type: str = 'default'):
        """Set value in cache with appropriate TTL."""
        cache_key = self._get_cache_key(key_parts)
        ttl = self.default_ttl.get(filing_type.lower(), self.default_ttl['default'])
        
        self.cache[cache_key] = {
            'value': value,
            'expires_at': datetime.now() + ttl,
            'filing_type': filing_type
        }
        logger.debug(f"Cache set for {cache_key}, expires in {ttl}")
    
    def clear(self):
        """Clear all cache entries."""
        self.cache.clear()
        logger.info("Cache cleared")


# Global cache instance
cache = Cache()


def cached(filing_type: str = 'default'):
    """Decorator to cache function results."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            key_parts = [func.__name__, args, sorted(kwargs.items())]
            
            # Check cache
            cached_value = cache.get(key_parts, filing_type)
            if cached_value is not None:
                return cached_value
            
            # Call function and cache result
            result = func(*args, **kwargs)
            cache.set(key_parts, result, filing_type)
            return result
        
        return wrapper
    return decorator


def parse_date(date_str: str) -> Optional[date]:
    """Parse various date formats from SEC filings."""
    if not date_str:
        return None
    
    # Common date formats in SEC filings
    date_formats = [
        "%Y-%m-%d",
        "%Y%m%d",
        "%m/%d/%Y",
        "%m-%d-%Y",
        "%d-%b-%Y",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z"
    ]
    
    for fmt in date_formats:
        try:
            parsed = datetime.strptime(date_str.strip(), fmt)
            return parsed.date()
        except ValueError:
            continue
    
    logger.warning(f"Could not parse date: {date_str}")
    return None


def parse_datetime(datetime_str: str) -> Optional[datetime]:
    """Parse various datetime formats from SEC filings."""
    if not datetime_str:
        return None
    
    # Common datetime formats in SEC filings
    datetime_formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%d %H:%M:%S",
        "%m/%d/%Y %I:%M:%S %p"
    ]
    
    for fmt in datetime_formats:
        try:
            return datetime.strptime(datetime_str.strip(), fmt)
        except ValueError:
            continue
    
    # Try parsing as date only
    parsed_date = parse_date(datetime_str)
    if parsed_date:
        return datetime.combine(parsed_date, datetime.min.time())
    
    logger.warning(f"Could not parse datetime: {datetime_str}")
    return None


def clean_number(value: Union[str, float, int]) -> Optional[float]:
    """Clean and convert string numbers to float."""
    if value is None:
        return None
    
    if isinstance(value, (int, float)):
        return float(value)
    
    # Remove common formatting
    cleaned = str(value).strip()
    cleaned = cleaned.replace(',', '')
    cleaned = cleaned.replace('$', '')
    cleaned = cleaned.replace('%', '')
    
    # Handle parentheses for negative numbers
    if cleaned.startswith('(') and cleaned.endswith(')'):
        cleaned = '-' + cleaned[1:-1]
    
    try:
        return float(cleaned)
    except ValueError:
        logger.warning(f"Could not parse number: {value}")
        return None


def normalize_cik(cik: str) -> str:
    """Normalize CIK to 10-digit format with leading zeros."""
    # Remove any non-numeric characters
    cik_clean = re.sub(r'\D', '', str(cik))
    # Pad with leading zeros to 10 digits
    return cik_clean.zfill(10)


def normalize_ticker(ticker: str) -> str:
    """Normalize ticker symbol."""
    if not ticker:
        return ""
    return ticker.upper().strip()


def build_filing_url(cik: str, accession_number: str, primary_document: str) -> str:
    """Build URL for accessing filing documents."""
    base_url = "https://www.sec.gov/Archives/edgar/data/"
    
    # Normalize CIK and accession number
    cik_norm = normalize_cik(cik).lstrip('0')  # Remove leading zeros for URL
    accession_clean = accession_number.replace('-', '')
    
    # Build path
    path = f"{cik_norm}/{accession_clean}/{primary_document}"
    
    return urljoin(base_url, path)


def extract_xml_url(filing_url: str) -> str:
    """Extract XML URL from filing URL."""
    # For Form 4, XML files typically have _doc.xml suffix
    if filing_url.endswith('.html') or filing_url.endswith('.htm'):
        base = filing_url.rsplit('.', 1)[0]
        return f"{base}_doc.xml"
    return filing_url


def retry_on_error(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator to retry function on error with exponential backoff."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                            f"Retrying in {current_delay} seconds..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"All {max_retries} attempts failed for {func.__name__}")
            
            raise last_exception
        
        return wrapper
    return decorator


def chunk_list(lst: list, chunk_size: int) -> list:
    """Split a list into chunks of specified size."""
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]


def format_currency(amount: float, currency: str = "USD") -> str:
    """Format currency amount for display."""
    if currency == "USD":
        return f"${amount:,.2f}"
    else:
        return f"{amount:,.2f} {currency}"


def calculate_percentage_change(old_value: float, new_value: float) -> Optional[float]:
    """Calculate percentage change between two values."""
    if old_value == 0:
        return None if new_value == 0 else float('inf')
    return ((new_value - old_value) / abs(old_value)) * 100


def extract_company_name_from_filing(filing_text: str) -> Optional[str]:
    """Extract company name from filing text."""
    # Common patterns for company names in filings
    patterns = [
        r'COMPANY CONFORMED NAME:\s*(.+?)(?:\n|$)',
        r'REGISTRANT NAME:\s*(.+?)(?:\n|$)',
        r'EXACT NAME OF REGISTRANT.*?:\s*(.+?)(?:\n|$)',
        r'<COMPANY-NAME>(.+?)</COMPANY-NAME>'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filing_text, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip()
    
    return None


def validate_cusip(cusip: str) -> bool:
    """Validate CUSIP format (9 characters)."""
    if not cusip or len(cusip) != 9:
        return False
    
    # CUSIP should be alphanumeric
    return cusip[:8].isalnum() and cusip[8].isdigit()


def merge_ownership_data(insider_data: list, institutional_data: list) -> Dict[str, Any]:
    """Merge insider and institutional ownership data."""
    total_insider_shares = sum(d.get('shares_owned', 0) for d in insider_data)
    total_institutional_shares = sum(d.get('shares_held', 0) for d in institutional_data)
    
    return {
        'total_shares': total_insider_shares + total_institutional_shares,
        'insider_shares': total_insider_shares,
        'institutional_shares': total_institutional_shares,
        'insider_count': len(insider_data),
        'institutional_count': len(institutional_data),
        'top_holders': sorted(
            insider_data + institutional_data,
            key=lambda x: x.get('shares_owned', x.get('shares_held', 0)),
            reverse=True
        )[:10]
    }