"""Intelligent name matching with fuzzy search capabilities."""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


@dataclass
class NameVariation:
    """Represents a name variation with confidence score."""
    original: str
    normalized: str
    variations: List[str]
    confidence: float


class IntelligentNameMatcher:
    """
    Intelligent name matching system that handles various name formats and variations.
    
    Addresses the limitation where "Gale Klappa" vs "KLAPPA GALE E" wouldn't match.
    """
    
    def __init__(self):
        # Common name prefixes and suffixes
        self.prefixes = {
            'mr', 'mrs', 'ms', 'dr', 'prof', 'sir', 'dame', 'lord', 'lady',
            'rev', 'father', 'sister', 'brother'
        }
        
        self.suffixes = {
            'jr', 'sr', 'ii', 'iii', 'iv', 'esq', 'md', 'phd', 'jd', 'cpa',
            'cfa', 'mba', 'pe', 'rn'
        }
        
        # Common nickname mappings
        self.nickname_map = {
            'bill': 'william', 'billy': 'william', 'will': 'william',
            'bob': 'robert', 'bobby': 'robert', 'rob': 'robert', 'robbie': 'robert',
            'dick': 'richard', 'rick': 'richard', 'ricky': 'richard', 'rich': 'richard',
            'jim': 'james', 'jimmy': 'james', 'jamie': 'james',
            'mike': 'michael', 'micky': 'michael', 'mickey': 'michael',
            'dave': 'david', 'davey': 'david',
            'steve': 'steven', 'stevie': 'steven',
            'chris': 'christopher', 'christi': 'christopher',
            'dan': 'daniel', 'danny': 'daniel',
            'tom': 'thomas', 'tommy': 'thomas',
            'tony': 'anthony', 'ant': 'anthony',
            'joe': 'joseph', 'joey': 'joseph',
            'ben': 'benjamin', 'benny': 'benjamin',
            'sam': 'samuel', 'sammy': 'samuel',
            'matt': 'matthew', 'matty': 'matthew',
            'nick': 'nicholas', 'nicky': 'nicholas',
            'andy': 'andrew', 'drew': 'andrew',
            'greg': 'gregory', 'greggy': 'gregory',
            'pat': 'patricia', 'patty': 'patricia', 'patti': 'patricia',
            'liz': 'elizabeth', 'beth': 'elizabeth', 'betty': 'elizabeth', 'betsy': 'elizabeth',
            'sue': 'susan', 'susie': 'susan', 'suzy': 'susan',
            'kathy': 'katherine', 'kate': 'katherine', 'katie': 'katherine', 'kit': 'katherine',
            'jen': 'jennifer', 'jenny': 'jennifer', 'jenn': 'jennifer',
            'amy': 'amelia', 'mel': 'amelia', 'melly': 'amelia'
        }
    
    def normalize_name(self, name: str) -> str:
        """
        Normalize a name by removing prefixes/suffixes and standardizing format.
        
        Examples:
        - "Mr. Gale E. Klappa Jr." -> "gale klappa"
        - "KLAPPA, GALE E" -> "gale klappa"
        - "Dr. William J. Smith III" -> "william smith"
        """
        if not name or not name.strip():
            return ""
        
        # Convert to lowercase and remove extra whitespace
        normalized = re.sub(r'\s+', ' ', name.lower().strip())
        
        # Remove punctuation
        normalized = re.sub(r'[.,;:!?]', '', normalized)
        
        # Handle comma-separated format ("Last, First Middle")
        if ',' in normalized:
            parts = [p.strip() for p in normalized.split(',')]
            if len(parts) >= 2:
                # "Last, First Middle" -> "First Middle Last"
                last_name = parts[0]
                first_parts = parts[1].split()
                normalized = f"{' '.join(first_parts)} {last_name}"
        
        # Split into words
        words = normalized.split()
        
        # Remove prefixes
        while words and words[0] in self.prefixes:
            words.pop(0)
        
        # Remove suffixes
        while words and words[-1] in self.suffixes:
            words.pop()
        
        # Remove single letters (middle initials)
        words = [word for word in words if len(word) > 1]
        
        # Convert nicknames to full names
        words = [self.nickname_map.get(word, word) for word in words]
        
        # Return normalized name
        return ' '.join(words)
    
    def calculate_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity score between two names (0.0 to 1.0)."""
        if not name1 or not name2:
            return 0.0
        
        # Normalize both names
        norm1 = self.normalize_name(name1)
        norm2 = self.normalize_name(name2)
        
        if norm1 == norm2:
            return 1.0
        
        # Check for partial matches
        words1 = set(norm1.split())
        words2 = set(norm2.split())
        
        if words1 and words2:
            # Calculate Jaccard similarity (intersection over union)
            intersection = len(words1 & words2)
            union = len(words1 | words2)
            jaccard = intersection / union if union > 0 else 0.0
            
            # Require at least 2 words to match for names
            if intersection >= 2:
                return jaccard
        
        # Use sequence matching as fallback
        sequence_similarity = SequenceMatcher(None, norm1, norm2).ratio()
        
        # Return higher score if above threshold
        return sequence_similarity if sequence_similarity > 0.8 else 0.0
    
    def is_name_match(self, name1: str, name2: str, threshold: float = 0.8) -> bool:
        """Check if two names refer to the same person."""
        similarity = self.calculate_similarity(name1, name2)
        return similarity >= threshold


# Global instance for easy access
name_matcher = IntelligentNameMatcher()


def smart_name_search(search_name: str, content: str, threshold: float = 0.8) -> bool:
    """Search for a person's name in content using intelligent matching."""
    
    # Direct text search with normalized names
    normalized_search = name_matcher.normalize_name(search_name)
    normalized_content = name_matcher.normalize_name(content)
    
    return normalized_search in normalized_content


def enhance_name_matching_in_search(person_name: str, xml_content: str) -> bool:
    """Enhanced name matching for insider transaction searches."""
    
    # Use smart name search first
    if smart_name_search(person_name, xml_content):
        return True
    
    # Try different name formats
    normalized_name = name_matcher.normalize_name(person_name)
    words = normalized_name.split()
    
    if len(words) >= 2:
        first_name = words[0]
        last_name = words[-1]
        
        # Check various formats
        variations = [
            f"{first_name} {last_name}",
            f"{last_name}, {first_name}",
            f"{last_name} {first_name}",
            f"{last_name.upper()}, {first_name.upper()}",
        ]
        
        xml_lower = xml_content.lower()
        
        for variation in variations:
            if variation.lower() in xml_lower:
                logger.debug(f"Name variation match: '{person_name}' found as '{variation}'")
                return True
    
    return False