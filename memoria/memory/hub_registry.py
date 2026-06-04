import logging
from typing import Set
from ..database.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)

class HubRegistry:
    """Caches and identifies high-degree entity 'hubs' in-memory to prevent neighborhood explosion."""
    
    def __init__(self, neo4j_client: Neo4jClient, degree_threshold: int = 50):
        self.client = neo4j_client
        self.threshold = degree_threshold
        self.hub_names: Set[str] = set()
        self.hub_ids: Set[str] = set()
        self.refresh()

    def refresh(self):
        """Fetches top high-degree nodes from Neo4j and caches them in memory."""
        if not self.client or not self.client.verify_connection():
            logger.debug("Neo4j offline. HubRegistry initialized empty.")
            return

        query = """
        MATCH (n:Entity)
        WHERE n.degree > $threshold
        RETURN n.id AS id, n.name AS name, n.degree AS degree
        """
        try:
            with self.client.driver.session(database=self.client.database) as session:
                res = session.run(query, threshold=self.threshold)
                new_hub_names = set()
                new_hub_ids = set()
                for record in res:
                    new_hub_names.add(record["name"])
                    new_hub_ids.add(record["id"])
                    
                self.hub_names = new_hub_names
                self.hub_ids = new_hub_ids
                logger.info(f"HubRegistry refreshed. Found {len(self.hub_names)} hub nodes (threshold > {self.threshold}).")
        except Exception as e:
            logger.error(f"Failed to refresh HubRegistry: {e}")

    def is_hub(self, entity_name_or_id: str) -> bool:
        """Checks if a given entity name or ID is registered as a high-degree hub."""
        return entity_name_or_id in self.hub_names or entity_name_or_id in self.hub_ids
