"""Data models for SEC EDGAR MCP server."""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from enum import Enum


class TransactionType(Enum):
    """Types of insider transactions."""
    PURCHASE = "P"
    SALE = "S"
    GIFT = "G"
    CONVERSION = "C"
    EXERCISE = "M"
    OTHER = "O"


class OwnershipType(Enum):
    """Types of ownership."""
    DIRECT = "D"
    INDIRECT = "I"


class PositionStatus(Enum):
    """Status of board/executive positions."""
    CURRENT = "current"
    FORMER = "former"
    UNKNOWN = "unknown"


class PositionType(Enum):
    """Types of corporate positions."""
    DIRECTOR = "Director"
    CHAIRMAN = "Chairman"
    CEO = "Chief Executive Officer"
    CFO = "Chief Financial Officer"
    COO = "Chief Operating Officer"
    PRESIDENT = "President"
    VICE_CHAIRMAN = "Vice Chairman"
    LEAD_DIRECTOR = "Lead Director"
    INDEPENDENT_DIRECTOR = "Independent Director"
    OTHER_OFFICER = "Other Officer"
    UNKNOWN = "Unknown"


@dataclass
class InsiderTransaction:
    """Represents an insider transaction from Form 4."""
    insider_name: str
    insider_title: Optional[str]
    company_name: str
    company_cik: str
    ticker: Optional[str]
    transaction_date: date
    transaction_type: TransactionType
    security_title: str
    shares: float
    price_per_share: Optional[float]
    total_value: Optional[float]
    ownership_type: OwnershipType
    shares_owned_after: float
    filing_date: datetime
    accession_number: str
    form_type: str  # 4 or 4/A
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "insider_name": self.insider_name,
            "insider_title": self.insider_title,
            "company_name": self.company_name,
            "company_cik": self.company_cik,
            "ticker": self.ticker,
            "transaction_date": self.transaction_date.isoformat(),
            "transaction_type": self.transaction_type.name,
            "security_title": self.security_title,
            "shares": self.shares,
            "price_per_share": self.price_per_share,
            "total_value": self.total_value,
            "ownership_type": self.ownership_type.name,
            "shares_owned_after": self.shares_owned_after,
            "filing_date": self.filing_date.isoformat(),
            "accession_number": self.accession_number,
            "form_type": self.form_type
        }


@dataclass
class InstitutionalHolding:
    """Represents institutional holdings from 13F filings."""
    institution_name: str
    institution_cik: Optional[str]
    report_date: date
    security_name: str
    security_cusip: str
    shares_held: int
    market_value: float
    percentage_of_portfolio: Optional[float]
    percentage_of_company: Optional[float]
    change_in_shares: Optional[int]
    change_percentage: Optional[float]
    filing_date: datetime
    accession_number: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "institution_name": self.institution_name,
            "institution_cik": self.institution_cik,
            "report_date": self.report_date.isoformat(),
            "security_name": self.security_name,
            "security_cusip": self.security_cusip,
            "shares_held": self.shares_held,
            "market_value": self.market_value,
            "percentage_of_portfolio": self.percentage_of_portfolio,
            "percentage_of_company": self.percentage_of_company,
            "change_in_shares": self.change_in_shares,
            "change_percentage": self.change_percentage,
            "filing_date": self.filing_date.isoformat(),
            "accession_number": self.accession_number
        }


@dataclass
class MajorShareholder:
    """Represents major shareholders from 13D/13G filings."""
    shareholder_name: str
    shareholder_type: str  # Individual, Institution, etc.
    shares_owned: int
    percentage_of_class: float
    filing_type: str  # 13D, 13G, etc.
    purpose_of_transaction: Optional[str]
    filing_date: datetime
    event_date: date
    accession_number: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "shareholder_name": self.shareholder_name,
            "shareholder_type": self.shareholder_type,
            "shares_owned": self.shares_owned,
            "percentage_of_class": self.percentage_of_class,
            "filing_type": self.filing_type,
            "purpose_of_transaction": self.purpose_of_transaction,
            "filing_date": self.filing_date.isoformat(),
            "event_date": self.event_date.isoformat(),
            "accession_number": self.accession_number
        }


@dataclass
class RevenueSegment:
    """Represents revenue by business segment."""
    segment_name: str
    revenue: float
    currency: str
    period_start: date
    period_end: date
    year_over_year_change: Optional[float]
    percentage_of_total: Optional[float]
    operating_income: Optional[float]
    filing_type: str  # 10-K, 10-Q
    filing_date: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "segment_name": self.segment_name,
            "revenue": self.revenue,
            "currency": self.currency,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "year_over_year_change": self.year_over_year_change,
            "percentage_of_total": self.percentage_of_total,
            "operating_income": self.operating_income,
            "filing_type": self.filing_type,
            "filing_date": self.filing_date.isoformat()
        }


@dataclass
class GeographicRevenue:
    """Represents revenue by geographic region."""
    region: str
    country: Optional[str]
    revenue: float
    currency: str
    period_start: date
    period_end: date
    percentage_of_total: Optional[float]
    filing_type: str
    filing_date: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "region": self.region,
            "country": self.country,
            "revenue": self.revenue,
            "currency": self.currency,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "percentage_of_total": self.percentage_of_total,
            "filing_type": self.filing_type,
            "filing_date": self.filing_date.isoformat()
        }


@dataclass
class MaterialEvent:
    """Represents material events from 8-K filings."""
    event_date: date
    event_type: str
    event_description: str
    company_name: str
    company_cik: str
    filing_date: datetime
    accession_number: str
    items_reported: List[str]
    exhibits: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "event_date": self.event_date.isoformat(),
            "event_type": self.event_type,
            "event_description": self.event_description,
            "company_name": self.company_name,
            "company_cik": self.company_cik,
            "filing_date": self.filing_date.isoformat(),
            "accession_number": self.accession_number,
            "items_reported": self.items_reported,
            "exhibits": self.exhibits
        }


@dataclass
class Filing:
    """Represents a generic SEC filing."""
    filing_type: str
    company_name: str
    company_cik: str
    ticker: Optional[str]
    filing_date: datetime
    period_of_report: Optional[date]
    accession_number: str
    file_number: Optional[str]
    primary_document: str
    primary_doc_description: Optional[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "filing_type": self.filing_type,
            "company_name": self.company_name,
            "company_cik": self.company_cik,
            "ticker": self.ticker,
            "filing_date": self.filing_date.isoformat(),
            "period_of_report": self.period_of_report.isoformat() if self.period_of_report else None,
            "accession_number": self.accession_number,
            "file_number": self.file_number,
            "primary_document": self.primary_document,
            "primary_doc_description": self.primary_doc_description
        }


@dataclass
class EntityActivityReport:
    """Comprehensive activity report for an entity."""
    entity_name: str
    entity_type: str  # Company, Person, Institution
    analysis_period_start: date
    analysis_period_end: date
    recent_filings: List[Filing]
    insider_transactions: List[InsiderTransaction]
    institutional_holdings: List[InstitutionalHolding]
    major_shareholders: List[MajorShareholder]
    material_events: List[MaterialEvent]
    revenue_segments: List[RevenueSegment]
    geographic_revenue: List[GeographicRevenue]
    summary_statistics: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "entity_name": self.entity_name,
            "entity_type": self.entity_type,
            "analysis_period_start": self.analysis_period_start.isoformat(),
            "analysis_period_end": self.analysis_period_end.isoformat(),
            "recent_filings": [f.to_dict() for f in self.recent_filings],
            "insider_transactions": [t.to_dict() for t in self.insider_transactions],
            "institutional_holdings": [h.to_dict() for h in self.institutional_holdings],
            "major_shareholders": [s.to_dict() for s in self.major_shareholders],
            "material_events": [e.to_dict() for e in self.material_events],
            "revenue_segments": [r.to_dict() for r in self.revenue_segments],
            "geographic_revenue": [g.to_dict() for g in self.geographic_revenue],
            "summary_statistics": self.summary_statistics
        }


@dataclass
class OwnershipSummary:
    """Summary of ownership for a specific entity in a company."""
    entity_name: str
    company_name: str
    company_ticker: Optional[str]
    total_shares_owned: int
    ownership_percentage: Optional[float]
    insider_shares: Optional[int]
    institutional_shares: Optional[int]
    last_updated: datetime
    recent_changes: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "entity_name": self.entity_name,
            "company_name": self.company_name,
            "company_ticker": self.company_ticker,
            "total_shares_owned": self.total_shares_owned,
            "ownership_percentage": self.ownership_percentage,
            "insider_shares": self.insider_shares,
            "institutional_shares": self.institutional_shares,
            "last_updated": self.last_updated.isoformat(),
            "recent_changes": self.recent_changes
        }


@dataclass
class ProductRevenueTrend:
    """Revenue trend for a specific product/segment over time."""
    product_name: str
    company_name: str
    revenue_data: List[Dict[str, Any]]  # List of {period, revenue, growth}
    total_revenue_period: float
    average_growth_rate: Optional[float]
    latest_revenue: float
    latest_period: date
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "product_name": self.product_name,
            "company_name": self.company_name,
            "revenue_data": self.revenue_data,
            "total_revenue_period": self.total_revenue_period,
            "average_growth_rate": self.average_growth_rate,
            "latest_revenue": self.latest_revenue,
            "latest_period": self.latest_period.isoformat()
        }


@dataclass
class BoardPosition:
    """Represents a board position with timeline tracking."""
    person_name: str
    person_cik: Optional[str]
    company_name: str
    company_cik: str
    ticker: Optional[str]
    position_type: PositionType
    position_status: PositionStatus
    appointment_date: Optional[date]
    resignation_date: Optional[date]
    committees: List[str]  # Committee memberships
    compensation: Optional[float]
    source_filing_type: str  # DEF 14A, 8-K, Form 4, etc.
    source_accession: str
    last_verified: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "person_name": self.person_name,
            "person_cik": self.person_cik,
            "company_name": self.company_name,
            "company_cik": self.company_cik,
            "ticker": self.ticker,
            "position_type": self.position_type.value,
            "position_status": self.position_status.value,
            "appointment_date": self.appointment_date.isoformat() if self.appointment_date else None,
            "resignation_date": self.resignation_date.isoformat() if self.resignation_date else None,
            "committees": self.committees,
            "compensation": self.compensation,
            "source_filing_type": self.source_filing_type,
            "source_accession": self.source_accession,
            "last_verified": self.last_verified.isoformat(),
            "is_current": self.position_status == PositionStatus.CURRENT,
            "duration_days": self._calculate_duration_days()
        }
    
    def _calculate_duration_days(self) -> Optional[int]:
        """Calculate duration of position in days."""
        if not self.appointment_date:
            return None
        
        end_date = self.resignation_date if self.resignation_date else date.today()
        return (end_date - self.appointment_date).days


@dataclass
class PersonCompanyMapping:
    """Maps a person to their relationship with a company."""
    person_name: str
    person_cik: Optional[str]
    company_name: str
    company_cik: str
    ticker: Optional[str]
    relationship_type: str  # "insider", "institutional", "both"
    current_positions: List[BoardPosition]
    former_positions: List[BoardPosition]
    total_transactions: int
    first_seen_date: date
    last_activity_date: date
    is_currently_active: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "person_name": self.person_name,
            "person_cik": self.person_cik,
            "company_name": self.company_name,
            "company_cik": self.company_cik,
            "ticker": self.ticker,
            "relationship_type": self.relationship_type,
            "current_positions": [p.to_dict() for p in self.current_positions],
            "former_positions": [p.to_dict() for p in self.former_positions],
            "total_positions": len(self.current_positions) + len(self.former_positions),
            "current_position_count": len(self.current_positions),
            "total_transactions": self.total_transactions,
            "first_seen_date": self.first_seen_date.isoformat(),
            "last_activity_date": self.last_activity_date.isoformat(),
            "is_currently_active": self.is_currently_active,
            "relationship_duration_days": (self.last_activity_date - self.first_seen_date).days
        }


@dataclass
class BoardChangeEvent:
    """Represents a board change event from 8-K filings."""
    company_name: str
    company_cik: str
    ticker: Optional[str]
    event_date: date
    event_type: str  # "appointment", "resignation", "retirement", "election"
    person_name: str
    position_type: PositionType
    effective_date: Optional[date]
    reason: Optional[str]
    source_filing: str  # 8-K accession number
    filing_date: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "company_name": self.company_name,
            "company_cik": self.company_cik,
            "ticker": self.ticker,
            "event_date": self.event_date.isoformat(),
            "event_type": self.event_type,
            "person_name": self.person_name,
            "position_type": self.position_type.value,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "reason": self.reason,
            "source_filing": self.source_filing,
            "filing_date": self.filing_date.isoformat()
        }


@dataclass
class ComprehensiveInsiderProfile:
    """Complete insider profile with cross-company analysis."""
    person_name: str
    person_cik: Optional[str]
    search_date: date
    company_relationships: List[PersonCompanyMapping]
    current_board_positions: List[BoardPosition]
    former_board_positions: List[BoardPosition]
    board_change_history: List[BoardChangeEvent]
    total_companies: int
    active_companies: int
    total_transactions: int
    summary_statistics: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "person_name": self.person_name,
            "person_cik": self.person_cik,
            "search_date": self.search_date.isoformat(),
            "company_relationships": [r.to_dict() for r in self.company_relationships],
            "current_board_positions": [p.to_dict() for p in self.current_board_positions],
            "former_board_positions": [p.to_dict() for p in self.former_board_positions],
            "board_change_history": [e.to_dict() for e in self.board_change_history],
            "summary": {
                "total_companies": self.total_companies,
                "active_companies": self.active_companies,
                "current_positions": len(self.current_board_positions),
                "former_positions": len(self.former_board_positions),
                "total_transactions": self.total_transactions,
                "board_changes": len(self.board_change_history)
            },
            "summary_statistics": self.summary_statistics
        }