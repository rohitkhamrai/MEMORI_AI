import logging
from typing import List, Dict, Any, Set
from ..database.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)

class GraphTraverser:
    """Traverses Neo4j graph with hub detection, community routing, and depth caps."""
    
    def __init__(self, neo4j_client: Neo4jClient):
        self.client = neo4j_client
        # Avoid circular import by fetching HubRegistry dynamically
        self._hub_registry = None

    @property
    def hub_registry(self):
        if self._hub_registry is None:
            try:
                from ..memory.hub_registry import HubRegistry
                self._hub_registry = HubRegistry(self.client)
            except Exception as e:
                logger.error(f"Failed to load HubRegistry: {e}")
        return self._hub_registry

    def is_bridge_entity(self, name: str) -> bool:
        """Determines if the entity is a bridge connecting multiple communities."""
        if not self.client or not self.client.verify_connection():
            return False
            
        # A node is a bridge if it connects to entities in a different community
        query = """
        MATCH (s:Entity) WHERE s.name = $name OR s.id = $name
        MATCH (s)-[:FACT]-(t:Entity)
        WHERE s.community_id IS NOT NULL AND t.community_id IS NOT NULL AND s.community_id <> t.community_id
        RETURN count(DISTINCT t.community_id) AS cross_community_count
        """
        try:
            with self.client.driver.session(database=self.client.database) as session:
                res = session.run(query, name=name)
                record = res.single()
                if record and record["cross_community_count"] >= 2:
                    return True
        except Exception as e:
            logger.debug(f"Failed to check bridge status for '{name}': {e}")
        return False

    def traverse(self, seed_names: List[str], max_depth: int = 2, max_results: int = 50) -> List[Dict[str, Any]]:
        """Traverses the graph starting from seed entity names.
        
        Governance features:
        - Hub Detection: Nodes with degree > 50 are not expanded past 1-hop.
        - Bridge Entity Protection: Bypasses hub limit if node is a community bridge.
        - Community Routing: Intra-community edges are processed and returned first.
        - Depth Caps: Enforced by max_depth parameter (Stage 0-1 = 2, Stage 2 = 3, Stage 3 = 4).
        """
        if not self.client or not self.client.verify_connection():
            logger.warning("Neo4j client not connected. Returning empty subgraph.")
            return []

        # Track visited nodes and returned relationships to avoid loops/duplicates
        visited_nodes: Set[str] = set()
        retrieved_relationships: List[Dict[str, Any]] = []
        retrieved_rel_ids: Set[str] = set()
        
        # Nodes to expand at the current depth
        current_seeds = set(seed_names)
        
        for depth in range(1, max_depth + 1):
            if not current_seeds or len(retrieved_relationships) >= max_results:
                break
                
            next_seeds: Set[str] = set()
            logger.info(f"Traversal depth {depth}/{max_depth} expanding {len(current_seeds)} seeds.")
            
            for seed in current_seeds:
                if seed in visited_nodes:
                    continue
                visited_nodes.add(seed)
                
                # Hub Detection
                is_hub_node = False
                if self.hub_registry:
                    is_hub_node = self.hub_registry.is_hub(seed)
                    
                # Bridge Entity Protection
                if is_hub_node and self.is_bridge_entity(seed):
                    logger.info(f"Bridge Entity Protection active for '{seed}'. Bypassing hub limit.")
                    is_hub_node = False
                    
                # If we reach a hub and we are NOT at the starting depth, skip deep expansion from it
                # to prevent neighborhood explosion. We can grab 1-hop connections, but won't queue neighbors.
                if is_hub_node and depth > 1:
                    logger.info(f"Hub node '{seed}' detected. Stopping further traversal from this path.")
                
                # Fetch outgoing relationships from Neo4j
                query = """
                MATCH (s:Entity) WHERE s.name = $name OR s.id = $name
                MATCH (s)-[r:FACT]->(t:Entity)
                RETURN 
                    s.name AS source, 
                    s.community_id AS s_community,
                    t.name AS target, 
                    t.community_id AS t_community,
                    r.predicate AS predicate,
                    r.claim AS claim,
                    r.confidence AS confidence,
                    r.id AS id,
                    r.created_at AS created_at
                """
                try:
                    with self.client.driver.session(database=self.client.database) as session:
                        res = session.run(query, name=seed)
                        
                        intra_community = []
                        cross_community = []
                        
                        for record in res:
                            rel_id = record["id"]
                            if rel_id in retrieved_rel_ids:
                                continue
                                
                            edge_data = {
                                "id": rel_id,
                                "source": record["source"],
                                "target": record["target"],
                                "predicate": record["predicate"],
                                "claim": record["claim"],
                                "confidence": record["confidence"],
                                "created_at": record["created_at"]
                            }
                            
                            # Community Routing: Segment by intra vs cross-community
                            s_comm = record["s_community"]
                            t_comm = record["t_community"]
                            
                            if s_comm is not None and t_comm is not None and s_comm == t_comm:
                                intra_community.append(edge_data)
                            else:
                                cross_community.append(edge_data)
                                
                        # Process intra-community first, then cross-community
                        all_edges = intra_community + cross_community
                        
                        for edge in all_edges:
                            if len(retrieved_relationships) >= max_results:
                                break
                            retrieved_relationships.append(edge)
                            retrieved_rel_ids.add(edge["id"])
                            
                            # Queue target for next depth expansion if seed is not a hub
                            if not is_hub_node and edge["target"] not in visited_nodes:
                                next_seeds.add(edge["target"])
                                
                except Exception as e:
                    logger.error(f"Error traversing from seed '{seed}': {e}")
                    
            current_seeds = next_seeds

        logger.info(f"Graph traversal completed. Retrieved {len(retrieved_relationships)} relationships.")
        return retrieved_relationships
