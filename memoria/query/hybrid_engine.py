import logging
from typing import Dict, Any, List
from ..router import CognitiveMaturityRouter, MaturityStage
from .vector_retrieval import VectorRetriever
from .graph_traversal import GraphTraverser
from ..database.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)

class HybridQueryEngine:
    """Combines vector search and graph traversal based on graph maturity."""
    
    def __init__(self, neo4j_client: Neo4jClient):
        self.client = neo4j_client
        self.vector_retriever = VectorRetriever(neo4j_client)
        self.graph_traverser = GraphTraverser(neo4j_client)

    def query(self, query_text: str, max_results: int = 50) -> Dict[str, Any]:
        """Queries the memory graph using a hybrid vector-graph model.
        
        Args:
            query_text: The user's query string.
            max_results: Upper bound on return sizes.
            
        Returns:
            Dict[str, Any]: Dictionary containing 'entities', 'relationships', and metadata.
        """
        # 1. Determine graph maturity stage based on triple count
        triple_count = 0
        if self.client and self.client.verify_connection():
            try:
                triple_count = self.client.get_triple_count()
            except Exception as e:
                logger.warning(f"Failed to fetch triple count: {e}")
                
        stage_enum = CognitiveMaturityRouter.get_stage(triple_count)
        
        if stage_enum == MaturityStage.BOOTSTRAP:
            stage = 0
            vector_weight = 0.80
            graph_weight = 0.05
            search_weight = 0.15
            max_depth = 2
        elif stage_enum == MaturityStage.SPARSE:
            stage = 1
            vector_weight = 0.60
            graph_weight = 0.25
            search_weight = 0.15
            max_depth = 2
        elif stage_enum == MaturityStage.STRUCTURED:
            stage = 2
            vector_weight = 0.40
            graph_weight = 0.40
            search_weight = 0.20
            max_depth = 3
        else:  # MaturityStage.COGNITIVE
            stage = 3
            vector_weight = 0.25
            graph_weight = 0.60
            search_weight = 0.15
            max_depth = 4

        logger.info(f"Hybrid retrieval executing under maturity Stage {stage} ({stage_enum.value}).")

        # 2. Perform Vector Retrieval
        vector_entities = []
        if vector_weight > 0.0:
            # Scale top_k based on weight
            top_k = max(5, int(max_results * vector_weight))
            vector_entities = self.vector_retriever.retrieve(query_text, top_k=top_k)
            
        # 3. Perform Graph Traversal
        graph_relationships = []
        if graph_weight > 0.0 and vector_entities:
            # Use retrieved vector entities as seeds
            seeds = [e["name"] for e in vector_entities]
            max_rel_count = max(5, int(max_results * graph_weight))
            graph_relationships = self.graph_traverser.traverse(
                seed_names=seeds,
                max_depth=max_depth,
                max_results=max_rel_count
            )
            
        # 4. If we are in Stage 0 (vector only) or we didn't traverse, fetch immediate relations of vector entities
        if not graph_relationships and vector_entities:
            seeds = [e["name"] for e in vector_entities]
            # Simple 1-hop traversal to enrich vector findings
            graph_relationships = self.graph_traverser.traverse(
                seed_names=seeds,
                max_depth=1,
                max_results=max_results
            )

        # Build list of unique entities present in relationships
        entities_map = {e["name"]: e for e in vector_entities}
        
        # Fetch detailed node info for entities in relationships that aren't in vector_entities
        needed_entity_names = set()
        for rel in graph_relationships:
            needed_entity_names.add(rel["source"])
            needed_entity_names.add(rel["target"])
            
        missing_names = needed_entity_names - set(entities_map.keys())
        if missing_names and self.client and self.client.verify_connection():
            # Batch query missing nodes
            query = "MATCH (n:Entity) WHERE n.name IN $names RETURN n.id AS id, n.name AS name, n.aliases AS aliases, n.description AS description, n.degree AS degree, n.community_id AS community_id"
            try:
                with self.client.driver.session(database=self.client.database) as session:
                    res = session.run(query, names=list(missing_names))
                    for record in res:
                        entities_map[record["name"]] = {
                            "id": record["id"],
                            "name": record["name"],
                            "aliases": record.get("aliases", []),
                            "description": record.get("description", ""),
                            "degree": record.get("degree", 0),
                            "community_id": record.get("community_id"),
                            "score": 0.5  # Neutral default score for non-vector hits
                        }
            except Exception as e:
                logger.error(f"Failed to fetch missing entity nodes: {e}")
                
        # Fill in dummy details if DB query failed or offline
        for name in missing_names:
            if name not in entities_map:
                entities_map[name] = {
                    "id": name,
                    "name": name,
                    "aliases": [],
                    "description": "Linked entity context.",
                    "degree": 1,
                    "community_id": None,
                    "score": 0.0
                }

        return {
            "stage": stage,
            "entities": list(entities_map.values()),
            "relationships": graph_relationships,
            "metadata": {
                "vector_weight": vector_weight,
                "graph_weight": graph_weight,
                "search_weight": search_weight,
                "max_depth": max_depth
            }
        }
