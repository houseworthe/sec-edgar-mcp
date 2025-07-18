"""Parser for SEC Form 4 XML documents."""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from xml.etree import ElementTree as ET
from bs4 import BeautifulSoup
import requests

from .models import InsiderTransaction, TransactionType, OwnershipType
from .utils import (
    parse_date, parse_datetime, clean_number, 
    normalize_cik, extract_xml_url, rate_limited
)

logger = logging.getLogger(__name__)


class Form4Parser:
    """Parser for Form 4 insider trading filings."""
    
    TRANSACTION_CODE_MAP = {
        'P': TransactionType.PURCHASE,
        'S': TransactionType.SALE,
        'G': TransactionType.GIFT,
        'C': TransactionType.CONVERSION,
        'M': TransactionType.EXERCISE,
        'F': TransactionType.SALE,  # Payment of exercise price
        'D': TransactionType.SALE,  # Disposition to issuer
        'A': TransactionType.PURCHASE,  # Grant/award
        'J': TransactionType.OTHER,
        'K': TransactionType.OTHER,
        'L': TransactionType.OTHER,
        'U': TransactionType.OTHER,
        'V': TransactionType.OTHER,
        'W': TransactionType.OTHER,
        'X': TransactionType.EXERCISE,
        'Z': TransactionType.OTHER
    }
    
    def __init__(self, user_agent: str):
        self.user_agent = user_agent
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': user_agent})
    
    @rate_limited
    def fetch_filing_content(self, url: str) -> Optional[str]:
        """Fetch filing content from URL."""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Error fetching filing from {url}: {e}")
            return None
    
    def parse_form4_xml(self, xml_content: str, accession_number: str) -> List[InsiderTransaction]:
        """Parse Form 4 XML content and extract transactions."""
        transactions = []
        
        try:
            # Parse XML - handle potential namespace issues
            # Remove namespace declarations for easier parsing
            xml_content_clean = xml_content
            if 'xmlns' in xml_content:
                # Strip default namespace to make parsing easier
                import re
                xml_content_clean = re.sub(r'xmlns[^=]*="[^"]*"', '', xml_content)
                xml_content_clean = re.sub(r'xmlns:[^=]*="[^"]*"', '', xml_content_clean)
            
            root = ET.fromstring(xml_content_clean)
            
            # Log root element for debugging
            logger.info(f"Parsing Form 4 XML - root element: {root.tag}")
            logger.debug(f"Root children: {[child.tag for child in root][:10]}")
            
            # Extract basic filing information
            filing_info = self._extract_filing_info(root)
            if not filing_info:
                logger.warning(f"Could not extract filing info from {accession_number}")
                # Log what we tried to find
                logger.debug(f"Looking for issuer: {root.find('.//issuer') is not None}")
                logger.debug(f"Looking for reportingOwner: {root.find('.//reportingOwner') is not None}")
                return transactions
            
            # Extract non-derivative transactions
            non_derivative_transactions = self._extract_non_derivative_transactions(
                root, filing_info, accession_number
            )
            transactions.extend(non_derivative_transactions)
            
            # Extract derivative transactions (options, warrants, etc.)
            derivative_transactions = self._extract_derivative_transactions(
                root, filing_info, accession_number
            )
            transactions.extend(derivative_transactions)
            
        except ET.ParseError as e:
            logger.error(f"Error parsing XML for {accession_number}: {e}")
            # Try alternative parsing with BeautifulSoup for malformed XML
            transactions = self._parse_with_beautifulsoup(xml_content, accession_number)
        
        return transactions
    
    def _extract_filing_info(self, root: ET.Element) -> Optional[Dict[str, Any]]:
        """Extract basic filing information from XML root."""
        info = {}
        
        # Extract issuer (company) information
        issuer = root.find('.//issuer')
        if issuer is not None:
            info['company_name'] = self._get_text(issuer, 'issuerName')
            info['company_cik'] = normalize_cik(self._get_text(issuer, 'issuerCik'))
            info['ticker'] = self._get_text(issuer, 'issuerTradingSymbol')
        
        # Extract reporting owner information - try multiple paths
        owner = root.find('.//reportingOwner')
        if owner is None:
            owner = root.find('reportingOwner')
        
        if owner is not None:
            # Try different paths for owner ID
            owner_id = owner.find('.//reportingOwnerId')
            if owner_id is None:
                owner_id = owner.find('reportingOwnerId')
            
            if owner_id is not None:
                # The name element might be 'rptOwnerName' or 'reportingOwnerName'
                info['insider_name'] = (
                    self._get_text(owner_id, 'rptOwnerName') or
                    self._get_text(owner_id, 'reportingOwnerName') or
                    self._get_text(owner_id, './/rptOwnerName') or
                    self._get_text(owner_id, './/reportingOwnerName')
                )
                info['insider_cik'] = self._get_text(owner_id, 'rptOwnerCik')
                
                logger.debug(f"Extracted insider name: {info.get('insider_name')}")
            
            # Extract relationships
            relationships = owner.find('.//reportingOwnerRelationship')
            if relationships is not None:
                titles = []
                if self._get_text(relationships, 'isDirector') == '1':
                    titles.append('Director')
                if self._get_text(relationships, 'isOfficer') == '1':
                    officer_title = self._get_text(relationships, 'officerTitle')
                    if officer_title:
                        titles.append(officer_title)
                if self._get_text(relationships, 'isTenPercentOwner') == '1':
                    titles.append('10% Owner')
                info['insider_title'] = ', '.join(titles) if titles else None
        
        # Extract period of report
        period = self._get_text(root, './/periodOfReport')
        if period:
            info['period_of_report'] = parse_date(period)
        
        # Extract filing date
        info['filing_date'] = datetime.now()  # Will be overridden with actual filing date
        
        # Extract form type
        info['form_type'] = self._get_text(root, './/documentType', '4')
        
        return info if info.get('company_name') and info.get('insider_name') else None
    
    def _extract_non_derivative_transactions(
        self, 
        root: ET.Element, 
        filing_info: Dict[str, Any],
        accession_number: str
    ) -> List[InsiderTransaction]:
        """Extract non-derivative transactions from Form 4."""
        transactions = []
        
        # Find non-derivative table - it might be a direct child or nested
        non_deriv_table = root.find('.//nonDerivativeTable')
        if non_deriv_table is None:
            non_deriv_table = root.find('nonDerivativeTable')
        
        if non_deriv_table is None:
            logger.debug(f"No nonDerivativeTable found in {accession_number}")
            return transactions
        
        logger.info(f"Found nonDerivativeTable with {len(non_deriv_table)} children")
        
        # Process each transaction - try both nested and direct children
        trans_elements = non_deriv_table.findall('.//nonDerivativeTransaction')
        if not trans_elements:
            trans_elements = non_deriv_table.findall('nonDerivativeTransaction')
        
        logger.info(f"Found {len(trans_elements)} nonDerivativeTransaction elements")
        
        for trans_elem in trans_elements:
            try:
                transaction = self._parse_non_derivative_transaction(
                    trans_elem, filing_info, accession_number
                )
                if transaction:
                    transactions.append(transaction)
            except Exception as e:
                logger.error(f"Error parsing non-derivative transaction: {e}")
        
        # Process holdings if no transactions
        if not transactions:
            for holding_elem in non_deriv_table.findall('.//nonDerivativeHolding'):
                try:
                    holding = self._parse_non_derivative_holding(
                        holding_elem, filing_info, accession_number
                    )
                    if holding:
                        transactions.append(holding)
                except Exception as e:
                    logger.error(f"Error parsing non-derivative holding: {e}")
        
        return transactions
    
    def _parse_non_derivative_transaction(
        self,
        trans_elem: ET.Element,
        filing_info: Dict[str, Any],
        accession_number: str
    ) -> Optional[InsiderTransaction]:
        """Parse a single non-derivative transaction."""
        try:
            # Extract security information
            security_title = self._get_text(trans_elem, './/securityTitle/value')
            if not security_title:
                return None
            
            # Extract transaction details
            trans_amounts = trans_elem.find('.//transactionAmounts')
            if trans_amounts is None:
                return None
            
            shares = clean_number(self._get_text(trans_amounts, './/transactionShares/value'))
            if shares is None:
                return None
            
            price_per_share = clean_number(
                self._get_text(trans_amounts, './/transactionPricePerShare/value')
            )
            
            # Extract transaction date
            trans_date_str = self._get_text(trans_elem, './/transactionDate/value')
            trans_date = parse_date(trans_date_str) if trans_date_str else filing_info.get('period_of_report')
            
            # Extract transaction code
            trans_coding = trans_elem.find('.//transactionCoding')
            trans_code = self._get_text(trans_coding, './/transactionCode') if trans_coding else 'P'
            trans_type = self.TRANSACTION_CODE_MAP.get(trans_code, TransactionType.OTHER)
            
            # Extract ownership information
            post_trans = trans_elem.find('.//postTransactionAmounts')
            shares_after = clean_number(
                self._get_text(post_trans, './/sharesOwnedFollowingTransaction/value')
            ) if post_trans else 0
            
            ownership = trans_elem.find('.//ownershipNature')
            ownership_type = OwnershipType.DIRECT
            if ownership is not None:
                direct_indirect = self._get_text(ownership, './/directOrIndirectOwnership/value')
                if direct_indirect and direct_indirect.upper() == 'I':
                    ownership_type = OwnershipType.INDIRECT
            
            # Calculate total value
            total_value = shares * price_per_share if price_per_share else None
            
            return InsiderTransaction(
                insider_name=filing_info['insider_name'],
                insider_title=filing_info.get('insider_title'),
                company_name=filing_info['company_name'],
                company_cik=filing_info['company_cik'],
                ticker=filing_info.get('ticker'),
                transaction_date=trans_date,
                transaction_type=trans_type,
                security_title=security_title,
                shares=shares,
                price_per_share=price_per_share,
                total_value=total_value,
                ownership_type=ownership_type,
                shares_owned_after=shares_after,
                filing_date=filing_info['filing_date'],
                accession_number=accession_number,
                form_type=filing_info['form_type']
            )
            
        except Exception as e:
            logger.error(f"Error in _parse_non_derivative_transaction: {e}")
            return None
    
    def _parse_non_derivative_holding(
        self,
        holding_elem: ET.Element,
        filing_info: Dict[str, Any],
        accession_number: str
    ) -> Optional[InsiderTransaction]:
        """Parse a non-derivative holding (no transaction, just ownership report)."""
        try:
            # Extract security information
            security_title = self._get_text(holding_elem, './/securityTitle/value')
            if not security_title:
                return None
            
            # Extract holding amounts
            post_trans = holding_elem.find('.//postTransactionAmounts')
            if post_trans is None:
                return None
            
            shares_owned = clean_number(
                self._get_text(post_trans, './/sharesOwnedFollowingTransaction/value')
            )
            if shares_owned is None:
                return None
            
            # Extract ownership information
            ownership = holding_elem.find('.//ownershipNature')
            ownership_type = OwnershipType.DIRECT
            if ownership is not None:
                direct_indirect = self._get_text(ownership, './/directOrIndirectOwnership/value')
                if direct_indirect and direct_indirect.upper() == 'I':
                    ownership_type = OwnershipType.INDIRECT
            
            # Create a "holding" transaction (no actual transaction occurred)
            return InsiderTransaction(
                insider_name=filing_info['insider_name'],
                insider_title=filing_info.get('insider_title'),
                company_name=filing_info['company_name'],
                company_cik=filing_info['company_cik'],
                ticker=filing_info.get('ticker'),
                transaction_date=filing_info.get('period_of_report'),
                transaction_type=TransactionType.OTHER,  # Holding report
                security_title=security_title,
                shares=0,  # No transaction
                price_per_share=None,
                total_value=None,
                ownership_type=ownership_type,
                shares_owned_after=shares_owned,
                filing_date=filing_info['filing_date'],
                accession_number=accession_number,
                form_type=filing_info['form_type']
            )
            
        except Exception as e:
            logger.error(f"Error in _parse_non_derivative_holding: {e}")
            return None
    
    def _extract_derivative_transactions(
        self,
        root: ET.Element,
        filing_info: Dict[str, Any],
        accession_number: str
    ) -> List[InsiderTransaction]:
        """Extract derivative transactions (options, warrants, etc.)."""
        transactions = []
        
        # Find derivative table
        deriv_table = root.find('.//derivativeTable')
        if deriv_table is None:
            return transactions
        
        # Process each transaction
        for trans_elem in deriv_table.findall('.//derivativeTransaction'):
            try:
                transaction = self._parse_derivative_transaction(
                    trans_elem, filing_info, accession_number
                )
                if transaction:
                    transactions.append(transaction)
            except Exception as e:
                logger.error(f"Error parsing derivative transaction: {e}")
        
        return transactions
    
    def _parse_derivative_transaction(
        self,
        trans_elem: ET.Element,
        filing_info: Dict[str, Any],
        accession_number: str
    ) -> Optional[InsiderTransaction]:
        """Parse a single derivative transaction."""
        try:
            # Extract security information
            security_title = self._get_text(trans_elem, './/securityTitle/value')
            if not security_title:
                return None
            
            # Extract conversion/exercise price
            conversion_price = clean_number(
                self._get_text(trans_elem, './/conversionOrExercisePrice/value')
            )
            
            # Extract transaction details
            trans_amounts = trans_elem.find('.//transactionAmounts')
            if trans_amounts is None:
                return None
            
            shares = clean_number(self._get_text(trans_amounts, './/transactionShares/value'))
            if shares is None:
                return None
            
            price_per_share = clean_number(
                self._get_text(trans_amounts, './/transactionPricePerShare/value')
            )
            
            # Extract transaction date
            trans_date_str = self._get_text(trans_elem, './/transactionDate/value')
            trans_date = parse_date(trans_date_str) if trans_date_str else filing_info.get('period_of_report')
            
            # Extract transaction code
            trans_coding = trans_elem.find('.//transactionCoding')
            trans_code = self._get_text(trans_coding, './/transactionCode') if trans_coding else 'M'
            trans_type = self.TRANSACTION_CODE_MAP.get(trans_code, TransactionType.OTHER)
            
            # Extract underlying security info
            underlying = trans_elem.find('.//underlyingSecurity')
            underlying_shares = 0
            if underlying is not None:
                underlying_shares = clean_number(
                    self._get_text(underlying, './/underlyingSecurityShares/value')
                ) or 0
            
            # Calculate total value
            total_value = shares * price_per_share if price_per_share else None
            
            return InsiderTransaction(
                insider_name=filing_info['insider_name'],
                insider_title=filing_info.get('insider_title'),
                company_name=filing_info['company_name'],
                company_cik=filing_info['company_cik'],
                ticker=filing_info.get('ticker'),
                transaction_date=trans_date,
                transaction_type=trans_type,
                security_title=f"{security_title} (Derivative)",
                shares=shares,
                price_per_share=price_per_share or conversion_price,
                total_value=total_value,
                ownership_type=OwnershipType.DIRECT,  # Default for derivatives
                shares_owned_after=underlying_shares,
                filing_date=filing_info['filing_date'],
                accession_number=accession_number,
                form_type=filing_info['form_type']
            )
            
        except Exception as e:
            logger.error(f"Error in _parse_derivative_transaction: {e}")
            return None
    
    def _parse_with_beautifulsoup(self, content: str, accession_number: str) -> List[InsiderTransaction]:
        """Fallback parser using BeautifulSoup for malformed XML."""
        transactions = []
        
        try:
            soup = BeautifulSoup(content, 'xml')
            
            # Extract filing info
            filing_info = {
                'company_name': soup.find('issuerName').text if soup.find('issuerName') else None,
                'company_cik': normalize_cik(soup.find('issuerCik').text) if soup.find('issuerCik') else None,
                'ticker': soup.find('issuerTradingSymbol').text if soup.find('issuerTradingSymbol') else None,
                'insider_name': soup.find('rptOwnerName').text if soup.find('rptOwnerName') else None,
                'filing_date': datetime.now(),
                'form_type': '4'
            }
            
            if not filing_info['company_name'] or not filing_info['insider_name']:
                return transactions
            
            # Extract officer title if present
            if soup.find('officerTitle'):
                filing_info['insider_title'] = soup.find('officerTitle').text
            
            # Parse non-derivative transactions
            for trans in soup.find_all('nonDerivativeTransaction'):
                try:
                    shares = float(trans.find('transactionShares').find('value').text)
                    price = trans.find('transactionPricePerShare')
                    price_value = float(price.find('value').text) if price and price.find('value') else None
                    
                    transaction = InsiderTransaction(
                        insider_name=filing_info['insider_name'],
                        insider_title=filing_info.get('insider_title'),
                        company_name=filing_info['company_name'],
                        company_cik=filing_info['company_cik'],
                        ticker=filing_info.get('ticker'),
                        transaction_date=parse_date(trans.find('transactionDate').find('value').text),
                        transaction_type=self.TRANSACTION_CODE_MAP.get(
                            trans.find('transactionCode').text, TransactionType.OTHER
                        ),
                        security_title=trans.find('securityTitle').find('value').text,
                        shares=shares,
                        price_per_share=price_value,
                        total_value=shares * price_value if price_value else None,
                        ownership_type=OwnershipType.DIRECT,
                        shares_owned_after=float(
                            trans.find('sharesOwnedFollowingTransaction').find('value').text
                        ),
                        filing_date=filing_info['filing_date'],
                        accession_number=accession_number,
                        form_type=filing_info['form_type']
                    )
                    transactions.append(transaction)
                except Exception as e:
                    logger.error(f"Error parsing transaction with BeautifulSoup: {e}")
            
        except Exception as e:
            logger.error(f"BeautifulSoup parsing failed for {accession_number}: {e}")
        
        return transactions
    
    def _get_text(self, element: ET.Element, path: str, default: str = None) -> Optional[str]:
        """Safely extract text from XML element."""
        if element is None:
            return default
        
        # Try direct path first
        found = element.find(path)
        if found is not None and found.text:
            return found.text.strip()
        
        # If path doesn't start with .// and we didn't find it, try with .//
        if not path.startswith('.//'):
            found = element.find('.//' + path)
            if found is not None and found.text:
                return found.text.strip()
        
        return default