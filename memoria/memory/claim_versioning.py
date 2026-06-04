import logging
import uuid
from typing import Dict, Any
from ..schema import IngestPayload
from ..database.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)

class ClaimVersioner:
    """Manages versioned storage of claims to prevent overwriting of information."""
    
    def __init__(self, neo4j_client: Neo4jClient):
        self.client = neo4j_client

    def ingest_resolved_payload(self, payload: IngestPayload, source_url: str) -> Dict[str, Any]:
        """Ingests resolved entities and relationships, creating version nodes for all relationships.
        
        Args:
            payload: Resolved IngestPayload (deduplicated entities).
            source_url: Source webpage URL.
            
        Returns:
            Dict[str, Any]: Ingest stats.
        """
        results = {
            "merged_nodes": [],
            "collision_nodes": [],
            "merged_relationships": [],
            "created_versions": 0
        }
        
        if not self.client or not self.client.verify_connection():
            logger.warning("Neo4j offline. Skipping versioned ingestion.")
            return results

        node_id_map: Dict[str, str] = {}
        
        with self.client.driver.session(database=self.client.database) as session:
            # 1. First merge all nodes (use the same logic as neo4j_client)
            for node in payload.nodes:
                is_collision = node.id.startswith("collision-")
                
                if is_collision:
                    collision_query = """
                    MERGE (n:Entity {id: $id})
                    ON CREATE SET
                        n.name = $name,
                        n.aliases = $aliases,
                        n.description = $description,
                        n.embedding = $embedding,
                        n.degree = 0,
                        n.community_id = $community_id,
                        n.last_updated = $last_updated,
                        n.collision_detected_at = datetime()
                    SET n:PotentialCollision
                    RETURN n.id AS id
                    """
                    session.run(collision_query, **node.model_dump())
                    results["collision_nodes"].append(node.name)
                    node_id_map[node.name] = node.id
                else:
                    merge_query = """
                    MERGE (n:Entity {name: $name})
                    ON CREATE SET 
                        n.id = $id,
                        n.aliases = $aliases,
                        n.description = $description,
                        n.embedding = $embedding,
                        n.degree = $degree,
                        n.community_id = $community_id,
                        n.last_updated = $last_updated
                    ON MATCH SET
                        n.description = n.description + " | " + $description,
                        n.embedding = case when $embedding is not null then $embedding else n.embedding end,
                        n.last_updated = $last_updated
                    RETURN n.id AS id
                    """
                    res = session.run(merge_query, **node.model_dump())
                    record = res.single()
                    node_id_map[node.name] = record["id"] if record else node.id
                    results["merged_nodes"].append(node.name)

            # 2. Process Relationships with Versioning
            from .quality import KnowledgeQualityManager
            quality_manager = KnowledgeQualityManager()

            for rel in payload.relationships:
                # Filter out low-quality claims
                if quality_manager.should_reject(rel):
                    logger.info(f"Skipping ingestion of low-quality claim: {rel.source} -[{rel.predicate}]-> {rel.target}")
                    continue

                source_id = node_id_map.get(rel.source, rel.source)
                target_id = node_id_map.get(rel.target, rel.target)
                
                version_id = str(uuid.uuid4())
                
                # Cypher query to merge FACT relationship and append ClaimVersion
                query = """
                MATCH (s:Entity) WHERE s.id = $source_id OR s.name = $source
                MATCH (t:Entity) WHERE t.id = $target_id OR t.name = $target
                
                // Merge direct relation
                MERGE (s)-[r:FACT {predicate: $predicate}]->(t)
                ON CREATE SET
                    r.id = $id,
                    r.claim = $claim,
                    r.confidence = $confidence,
                    r.created_at = $created_at,
                    r.ttl_days = $ttl_days,
                    r.version_count = 1
                ON MATCH SET
                    r.version_count = coalesce(r.version_count, 1) + 1,
                    r.confidence = (r.confidence + $confidence) / 2.0,
                    r.claim = r.claim + " | " + $claim,
                    r.last_updated = $created_at
                
                // Create version node
                CREATE (v:ClaimVersion {
                    id: $version_id,
                    version: coalesce(r.version_count, 1),
                    claim: $claim,
                    confidence: $confidence,
                    source_url: $source_url,
                    created_at: $created_at
                })
                
                // Link version to source and target
                CREATE (s)-[:HAS_VERSION {predicate: $predicate, rel_id: r.id}]->(v)
                CREATE (v)-[:HAS_VERSION {rel_id: r.id}]->(t)
                
                // Update degree
                SET s.degree = s.degree + 1, t.degree = t.degree + 1
                
                RETURN r.id AS rel_id, r.version_count AS version_num
                """
                try:
                    res = session.run(
                        query,
                        source_id=source_id,
                        target_id=target_id,
                        source=rel.source,
                        target=rel.target,
                        predicate=rel.predicate,
                        id=rel.id,
                        claim=rel.claim,
                        confidence=rel.confidence,
                        created_at=rel.created_at,
                        ttl_days=rel.ttl_days,
                        version_id=version_id,
                        source_url=source_url
                    )
                    record = res.single()
                    results["merged_relationships"].append(f"{rel.source} -[{rel.predicate}]-> {rel.target}")
                    results["created_versions"] += 1
                except Exception as e:
                    logger.error(f"Failed to version relationship {rel.source} -[{rel.predicate}]-> {rel.target}: {e}")

        return results
