import logging
from typing import Dict, List, Set, Any
from ..schema import IngestPayload, EntityNode, RelationshipEdge
from ..database.neo4j_client import Neo4jClient
from ..embeddings import EmbeddingEngine

logger = logging.getLogger(__name__)

class EntityResolver:
    """Resolves entity duplication and handles namespace collisions using topological context."""
    
    def __init__(self, neo4j_client: Neo4jClient):
        self.client = neo4j_client
        self.embedding_engine = EmbeddingEngine()

    def find_similar_existing_nodes(self, node: EntityNode) -> List[Dict[str, Any]]:
        """Queries Neo4j for nodes with matching names, aliases, or high embedding similarity (>0.88)."""
        if not self.client or not self.client.verify_connection():
            return []
            
        # 1. First check exact name
        exact_query = "MATCH (n:Entity {name: $name}) RETURN n.id AS id, n.name AS name, n.aliases AS aliases, 1.0 AS score"
        try:
            with self.client.driver.session(database=self.client.database) as session:
                res = session.run(exact_query, name=node.name)
                record = res.single()
                if record:
                    return [{
                        "id": record["id"],
                        "name": record["name"],
                        "aliases": record.get("aliases", []),
                        "score": 1.0
                    }]
        except Exception as e:
            logger.error(f"Error checking exact name match: {e}")

        # 2. Next check aliases
        alias_query = "MATCH (n:Entity) WHERE $name IN n.aliases RETURN n.id AS id, n.name AS name, n.aliases AS aliases, 0.95 AS score"
        try:
            with self.client.driver.session(database=self.client.database) as session:
                res = session.run(alias_query, name=node.name)
                record = res.single()
                if record:
                    return [{
                        "id": record["id"],
                        "name": record["name"],
                        "aliases": record.get("aliases", []),
                        "score": 0.95
                    }]
        except Exception as e:
            logger.error(f"Error checking alias match: {e}")

        # 3. Last check embedding similarity using vector index
        if node.embedding:
            vector_query = """
            CALL db.index.vector.queryNodes('entity_embeddings', 3, $embedding)
            YIELD node, score
            WHERE score >= 0.88
            RETURN node.id AS id, node.name AS name, node.aliases AS aliases, score
            """
            try:
                with self.client.driver.session(database=self.client.database) as session:
                    res = session.run(vector_query, embedding=node.embedding)
                    matches = []
                    for record in res:
                        matches.append({
                            "id": record["id"],
                            "name": record["name"],
                            "aliases": record.get("aliases", []),
                            "score": record["score"]
                        })
                    return matches
            except Exception as e:
                logger.error(f"Error checking vector similarity match: {e}")
                
        return []

    def resolve(self, payload: IngestPayload) -> IngestPayload:
        """Resolves duplicates and collisions in the incoming payload.
        
        Maps incoming names to canonical database names or collision names.
        """
        if not self.client or not self.client.verify_connection():
            logger.warning("Neo4j offline. Skipping entity resolution.")
            return payload
            
        resolved_nodes: List[EntityNode] = []
        name_map: Dict[str, str] = {}  # Map from original name to resolved name
        
        # Build neighbor maps for incoming payload to run structural connection checks
        incoming_neighbors: Dict[str, List[str]] = {}
        for rel in payload.relationships:
            incoming_neighbors.setdefault(rel.source, []).append(rel.target)
            incoming_neighbors.setdefault(rel.target, []).append(rel.source)

        for node in payload.nodes:
            similar_nodes = self.find_similar_existing_nodes(node)
            
            if not similar_nodes:
                # No duplicate found. Keeps original identity
                resolved_nodes.append(node)
                name_map[node.name] = node.name
                continue
                
            # Grab highest scoring match
            best_match = max(similar_nodes, key=lambda x: x["score"])
            matched_name = best_match["name"]
            
            # Run Topological Context Check
            neighbors = incoming_neighbors.get(node.name, [])
            overlap = self.client.check_structural_connection(matched_name, neighbors)
            
            if overlap == 0.0 and best_match["score"] < 1.0:
                # High similarity, but entirely different context -> COLLISION
                logger.warning(f"Collision detected! '{node.name}' has high similarity to '{matched_name}' but 0.0 structural connection.")
                
                # Append collision identifier to ensure it goes to the PotentialDuplicate queue
                collision_name = f"{node.name} (Collision {node.id[:8]})"
                collision_node = EntityNode(
                    id=f"collision-{node.id}",
                    name=collision_name,
                    aliases=node.aliases,
                    description=node.description + f" [COLLISION with existing node {matched_name}]",
                    embedding=node.embedding,
                    degree=0,
                    community_id=node.community_id,
                    last_updated=node.last_updated
                )
                resolved_nodes.append(collision_node)
                name_map[node.name] = collision_name
            else:
                # Same context (or exact name/alias match) -> MERGE
                logger.info(f"Resolving '{node.name}' -> existing node '{matched_name}'")
                
                # Update aliases on node
                aliases_set = set(best_match.get("aliases", []) or [])
                aliases_set.add(node.name)
                for a in node.aliases:
                    aliases_set.add(a)
                    
                # Update payload mapping
                name_map[node.name] = matched_name
                
                # Create merged node to set fields on update
                merged_node = EntityNode(
                    id=best_match["id"],
                    name=matched_name,
                    aliases=list(aliases_set),
                    description=node.description,
                    embedding=node.embedding,
                    degree=node.degree,
                    community_id=node.community_id,
                    last_updated=node.last_updated
                )
                resolved_nodes.append(merged_node)

        # Rebuild relationships using the resolved entity names
        resolved_relationships: List[RelationshipEdge] = []
        for rel in payload.relationships:
            resolved_source = name_map.get(rel.source, rel.source)
            resolved_target = name_map.get(rel.target, rel.target)
            
            resolved_rel = RelationshipEdge(
                id=rel.id,
                source=resolved_source,
                target=resolved_target,
                predicate=rel.predicate,
                claim=rel.claim,
                confidence=rel.confidence,
                created_at=rel.created_at,
                ttl_days=rel.ttl_days
            )
            resolved_relationships.append(resolved_rel)

        return IngestPayload(nodes=resolved_nodes, relationships=resolved_relationships)
