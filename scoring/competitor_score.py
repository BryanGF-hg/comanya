import math
from typing import List, Dict, Any
from models.company import Company

class CompetitorScorer:
    def __init__(self, config):
        self.config = config
        self.weights = config['scoring']['weights']
        self.size_min_multiplier = config['scoring']['size_multiplier']['min']
        self.size_max_multiplier = config['scoring']['size_multiplier']['max']
        self.geo_priority = config['scoring']['geographic_priority']
    
    def calculate_geographic_score(self, lead_company: Company, competitor: Company) -> float:
        """Calcula score basado en proximidad geográfica"""
        if not competitor.city and not competitor.province:
            return 0.0
        
        # Mismo municipio
        if competitor.city and competitor.city.lower() == lead_company.city.lower():
            return 1.0
        # Misma provincia
        elif competitor.province and competitor.province.lower() == lead_company.province.lower():
            return 0.7
        # Misma comunidad autónoma (simplificado)
        elif competitor.province:
            return 0.4
        else:
            return 0.1
    
    def calculate_size_score(self, lead_company: Company, competitor: Company) -> float:
        """Calcula score basado en tamaño relativo (3-20x es ideal)"""
        if not lead_company.employees or not competitor.employees:
            if lead_company.revenue and competitor.revenue:
                lead_size = lead_company.revenue
                comp_size = competitor.revenue
            else:
                return 0.5  # Score neutral si no hay datos
        
        lead_size = lead_company.employees or lead_company.revenue or 1
        comp_size = competitor.employees or competitor.revenue or 1
        
        if lead_size <= 0:
            lead_size = 1
        
        ratio = comp_size / lead_size
        
        if self.size_min_multiplier <= ratio <= self.size_max_multiplier:
            # Ratio ideal, score máximo
            return 1.0
        elif ratio < self.size_min_multiplier:
            # Más pequeño que el ideal, penalizar proporcionalmente
            return ratio / self.size_min_multiplier
        else:
            # Más grande que el ideal, penalizar suavemente
            return math.exp(-(ratio - self.size_max_multiplier) / self.size_max_multiplier)
    
    def calculate_licenses_score(self, competitor: Company) -> float:
        """Calcula score basado en licitaciones ganadas"""
        max_licenses = 100  # Referencia máxima esperada
        score = min(competitor.licenses_won_24m / max_licenses, 1.0)
        return score
    
    def calculate_reviews_score(self, competitor: Company) -> float:
        """Calcula score basado en reseñas de Google"""
        max_reviews = 1000  # Referencia máxima
        score = min(competitor.google_reviews / max_reviews, 1.0)
        return score
    
    def calculate_total_score(self, lead_company: Company, competitor: Company) -> float:
        """Calcula score total del competidor"""
        competitor.geographic_score = self.calculate_geographic_score(lead_company, competitor)
        competitor.size_score = self.calculate_size_score(lead_company, competitor)
        competitor.licenses_score = self.calculate_licenses_score(competitor)
        competitor.reviews_score = self.calculate_reviews_score(competitor)
        
        total = (
            competitor.geographic_score * self.weights['geographic_proximity'] +
            competitor.size_score * self.weights['relative_size'] +
            competitor.licenses_score * self.weights['licenses_won_24m'] +
            competitor.reviews_score * self.weights['google_reviews_score']
        )
        
        competitor.total_score = total
        return total
    
    def rank_competitors(self, lead_company: Company, competitors: List[Company]) -> List[Company]:
        """Ranking de competidores por score"""
        for comp in competitors:
            self.calculate_total_score(lead_company, comp)
        
        # Ordenar por score descendente
        ranked = sorted(competitors, key=lambda x: x.total_score, reverse=True)
        return ranked
    
    def get_top_competitors(self, lead_company: Company, competitors: List[Company], 
                           top_n: int = 3, secondary_n: int = 2) -> Dict[str, List[Company]]:
        """Obtiene top competidores y secundarios"""
        ranked = self.rank_competitors(lead_company, competitors)
        
        # Excluir el lead si está en la lista
        ranked = [c for c in ranked if c.name.lower() != lead_company.name.lower()]
        
        return {
            'top': ranked[:top_n],
            'secondary': ranked[top_n:top_n + secondary_n]
        }
