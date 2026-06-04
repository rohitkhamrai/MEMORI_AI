import logging
from typing import List, Dict, Any
from ..embeddings import EmbeddingEngine
from ..database.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)

class VectorRetriever:
    """Performs approximate nearest neighbor (ANN) vector search on Entity nodes in Neo4j."""
    
    def __init__(self, neo4j_client: Neo4jClient):
        self.client = neo4j_client
        self.embedding_engine = EmbeddingEngine()

    def retrieve(self, query_text: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Retrieves top-k closest entities based on vector cosine similarity.
        
        Args:
            query_text: The search query.
            top_k: Max entities to return.
            
        Returns:
            List[Dict[str, Any]]: List of dictionary representations of matched entities with scores.
        """
        # Get query embedding
        query_vector = self.embedding_engine.get_embedding(query_text)
        if not query_vector:
            logger.warning("Could not generate query embedding. Returning empty results.")
            return []
            
        if not self.client or not self.client.verify_connection():
            logger.warning("Neo4j client not available or not connected. Returning empty results.")
            return []

        query = """
        CALL db.index.vector.queryNodes('entity_embeddings', $top_k, $query_vector)
        YIELD node, score
        RETURN 
            node.id AS id, 
            node.name AS name, 
            node.aliases AS aliases, 
            node.description AS description, 
            node.degree AS degree,
            node.community_id AS community_id,
            score
        """
        results = []
        try:
            with self.client.driver.session(database=self.client.database) as session:
                res = session.run(query, top_k=top_k, query_vector=query_vector)
                for record in res:
                    results.append({
                        "id": record["id"],
                        "name": record["name"],
                        "aliases": record.get("aliases", []),
                        "description": record.get("description", ""),
                        "degree": record.get("degree", 0),
                        "community_id": record.get("community_id"),
                        "score": record["score"]
                    })
            logger.info(f"Vector search retrieved {len(results)} matches for '{query_text}'.")
            return results
        except Exception as e:
            logger.error(f"Vector retrieval failed in Neo4j: {e}")
            return []
