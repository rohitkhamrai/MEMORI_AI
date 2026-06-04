import logging
from typing import Dict, Any
from ..schema import RelationshipEdge

logger = logging.getLogger(__name__)

class KnowledgeQualityManager:
    """Evaluates knowledge importance, filters out noise, and rejects low-quality claims."""
    
    def __init__(self, confidence_floor: float = 0.20, composite_floor: float = 0.25):
        self.confidence_floor = confidence_floor
        self.composite_floor = composite_floor

    def calculate_importance(self, source_authority: float, query_frequency: int, recency_score: float, degree: int) -> float:
        """Calculates memory importance score.
        
        Formula: 0.4 * source_authority + 0.3 * query_frequency_norm + 0.2 * recency_score + 0.1 * centrality_norm
        """
        # Normalize query frequency (cap at 10)
        query_freq_norm = min(1.0, float(query_frequency) / 10.0)
        
        # Normalize centrality / degree (cap at 50)
        centrality_norm = min(1.0, float(degree) / 50.0)
        
        importance = (
            0.4 * source_authority +
            0.3 * query_freq_norm +
            0.2 * recency_score +
            0.1 * centrality_norm
        )
        return round(importance, 4)

    def should_reject(self, rel: RelationshipEdge, source_score: float = 1.0) -> bool:
        """Determines if a claim should be rejected based on confidence and score thresholds.
        
        Args:
            rel: The relationship edge to evaluate.
            source_score: The combined source score (authority * recency).
            
        Returns:
            bool: True if the claim should be rejected, False to allow it.
        """
        # Composite score is confidence * source_score
        composite_score = rel.confidence * source_score
        
        # Check thresholds
        if rel.confidence < self.confidence_floor:
            logger.warning(f"Rejecting claim: Confidence {rel.confidence:.2f} below floor ({self.confidence_floor}).")
            return True
            
        if composite_score < self.composite_floor:
            logger.warning(f"Rejecting claim: Composite score {composite_score:.2f} below floor ({self.composite_floor}).")
            return True
            
        return False
