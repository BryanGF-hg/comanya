from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime

@dataclass
class Company:
    # Información básica
    name: str
    cnae: str
    city: str
    province: str
    
    # Datos de contacto (de ContactScraper)
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    
    # Datos de dirección (de AddressScraper)
    address: Optional[str] = None
    municipality: Optional[str] = None
    postal_code: Optional[str] = None
    
    # Datos empresariales (de FinancialScraper)
    employees: Optional[int] = None
    revenue: Optional[float] = None  # en millones EUR
    founding_year: Optional[int] = None
    cif: Optional[str] = None  # CIF/NIF
    legal_form: Optional[str] = None
    
    # Datos de competencia (de CompetitorDetailsScraper)
    google_reviews: int = 0
    google_rating: float = 0.0
    trustpilot_reviews: int = 0
    trustpilot_rating: float = 0.0
    licenses_won_24m: int = 0
    total_licenses: int = 0
    ranking: Optional[int] = None
    
    # Redes sociales (de SocialMediaScraper)
    linkedin: Optional[str] = None
    twitter: Optional[str] = None
    facebook: Optional[str] = None
    instagram: Optional[str] = None
    
    # Growth (de FinancialScraper)
    growth_rate: Optional[float] = None
    profit_margin: Optional[float] = None
    
    # Scores
    geographic_score: float = 0.0
    size_score: float = 0.0
    licenses_score: float = 0.0
    reviews_score: float = 0.0
    total_score: float = 0.0
    
    # Metadata
    source_url: Optional[str] = None
    last_updated: datetime = field(default_factory=datetime.now)

@dataclass
class CompetitorAnalysis:
    lead_company: Company
    competitors: List[Company]
    top_competitors: List[Company] = field(default_factory=list)
    secondary_competitors: List[Company] = field(default_factory=list)
    analysis_date: datetime = field(default_factory=datetime.now)
