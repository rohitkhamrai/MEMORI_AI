import math
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any
from ..database.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)

class TemporalDecayEngine:
    """Calculates exponential memory stability decay and identifies stale knowledge graph contexts."""
    
    def __init__(self, neo4j_client: Neo4jClient | None = None):
        self.client = neo4j_client

    @staticmethod
    def compute_stability_index(created_at_str: str, ttl_days: int = 90) -> float:
        """Computes current stability index using the formula: e^(-age_seconds / ttl_seconds).
        
        Args:
            created_at_str: ISO 8601 timestamp string.
            ttl_days: TTL horizon frame.
            
        Returns:
            float: Stability index value between 0.0 and 1.0.
        """
        try:
            # Parse ISO datetime
            clean_str = created_at_str.replace("Z", "+00:00")
            created_dt = datetime.fromisoformat(clean_str)
            
            age_seconds = (datetime.now(timezone.utc) - created_dt).total_seconds()
            if age_seconds < 0:
                age_seconds = 0
                
            ttl_seconds = ttl_days * 24 * 3600
            
            if ttl_seconds <= 0:
                return 0.0
                
            stability = math.exp(-age_seconds / ttl_seconds)
            return round(stability, 4)
        except Exception as e:
            logger.warning(f"Error computing stability index for {created_at_str}: {e}")
            return 1.0

    def scan_for_stale(self, threshold_days: int = 90) -> List[Dict[str, Any]]:
        """Scans database for relationships past their TTL or exceeding threshold_days.
        
        Args:
            threshold_days: Max age threshold in days.
            
        Returns:
            List[Dict[str, Any]]: List of stale relationships.
        """
        if not self.client:
            logger.warning("No Neo4jClient configured in TemporalDecayEngine.")
            return []
            
        stale_relationships = self.client.get_stale_relationships(threshold_days)
        
        # Flags them as stale in DB
        for rel in stale_relationships:
            self.client.flag_stale(rel["id"])
            
        return stale_relationships
