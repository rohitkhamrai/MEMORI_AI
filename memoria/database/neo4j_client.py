from neo4j import GraphDatabase
from typing import List, Dict, Any, Optional
from ..schema import EntityNode, RelationshipEdge, IngestPayload
import logging

logger = logging.getLogger(__name__)

class Neo4jClient:
    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password), connection_timeout=1.0, connection_acquisition_timeout=1.0)
        self.database = database

    def close(self):
        self.driver.close()

    def verify_connection(self) -> bool:
        try:
            with self.driver.session(database=self.database) as session:
                session.run("RETURN 1")
            return True
        except Exception as e:
            logger.error(f"Neo4j connection failed: {e}")
            return False

    def get_triple_count(self) -> int:
        query = "MATCH ()-[r]->() RETURN count(r) AS count"
        with self.driver.session(database=self.database) as session:
            result = session.run(query)
            record = result.single()
            return record["count"] if record else 0

    def initialize_vector_index(self, dimension: int = 384):
        """
        Creates a vector index on the embedding property of Entity nodes in Neo4j 5.x.
        """
        query = f"""
        CREATE VECTOR INDEX entity_embeddings IF NOT EXISTS
        FOR (n:Entity) ON (n.embedding)
        OPTIONS {{
            indexConfig: {{
                `vector.dimensions`: {dimension},
                `vector.similarity_function`: 'cosine'
            }}
        }}
        """
        with self.driver.session(database=self.database) as session:
            session.run(query)

    def check_structural_connection(self, entity_name: str, incoming_neighbors: List[str]) -> float:
        """
        Calculates the structural connection index between an existing entity and incoming neighbor entities.
        Returns 0.0 if there is absolutely no path of length <= 2 in the graph between the entity and
        any of the incoming neighbors, else returns 1.0.
        """
        if not incoming_neighbors:
            return 1.0  # No neighbors to compare against, default to allowing merge

        query = """
        MATCH (e:Entity {name: $entity_name})
        MATCH (neighbor:Entity) WHERE neighbor.name IN $neighbors
        MATCH p = shortestPath((e)-[*..2]-(neighbor))
        RETURN count(p) AS path_count
        """
        with self.driver.session(database=self.database) as session:
            result = session.run(query, entity_name=entity_name, neighbors=incoming_neighbors)
            record = result.single()
            count = record["path_count"] if record else 0
            return 1.0 if count > 0 else 0.0

    def ingest_payload(self, payload: IngestPayload) -> Dict[str, Any]:
        """
        Ingests a payload of nodes and relationships into Neo4j.
        Implements the Topological Context Break to avoid namespace collisions.
        """
        results = {
            "merged_nodes": [],
            "collision_nodes": [],
            "merged_relationships": []
        }

        # Build neighbor maps for incoming nodes to check context
        incoming_neighbors: Dict[str, List[str]] = {}
        for rel in payload.relationships:
            incoming_neighbors.setdefault(rel.source, []).append(rel.target)
            incoming_neighbors.setdefault(rel.target, []).append(rel.source)

        node_id_map: Dict[str, str] = {}  # Map from original name/ID to actual merged Node ID in DB

        with self.driver.session(database=self.database) as session:
            # 1. Process Nodes
            for node in payload.nodes:
                # Check for existing node with same name
                check_query = "MATCH (n:Entity {name: $name}) RETURN n.id AS id"
                check_res = session.run(check_query, name=node.name)
                record = check_res.single()

                is_collision = False
                if record:
                    # Existing node found. Check structural connection context
                    neighbors = incoming_neighbors.get(node.name, [])
                    conn_index = self.check_structural_connection(node.name, neighbors)
                    if conn_index == 0.0:
                        # Collision! Different context. Terminate automated convergence.
                        is_collision = True

                if is_collision:
                    # Redirect to Potential Duplicate Queue (marked with label 'PotentialCollision')
                    collision_query = """
                    CREATE (n:PotentialCollision:Entity {
                        id: $id,
                        name: $name,
                        aliases: $aliases,
                        description: $description,
                        embedding: $embedding,
                        degree: 0,
                        community_id: $community_id,
                        last_updated: $last_updated,
                        collision_detected_at: datetime()
                    })
                    RETURN n.id AS id
                    """
                    params = node.model_dump()
                    params["id"] = f"collision-{node.id}"
                    params["name"] = f"{node.name} (Collision {node.id[:8]})"
                    session.run(collision_query, **params)
                    results["collision_nodes"].append(node.name)
                    node_id_map[node.name] = params["id"]
                else:
                    # Merge Node normally
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
                        n.aliases = apoc.coll.union(n.aliases, $aliases),
                        n.description = n.description + " | " + $description,
                        n.embedding = coalesce($embedding, n.embedding),
                        n.last_updated = $last_updated
                    RETURN n.id AS id
                    """
                    # Note: apoc is standard but we'll use a pure Cypher alternative for robustness
                    merge_query_pure = """
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
                    res = session.run(merge_query_pure, **node.model_dump())
                    record = res.single()
                    node_id_map[node.name] = record["id"] if record else node.id
                    results["merged_nodes"].append(node.name)

            # 2. Process Relationships
            for rel in payload.relationships:
                # Find source and target IDs in DB mapping
                source_id = node_id_map.get(rel.source, rel.source)
                target_id = node_id_map.get(rel.target, rel.target)

                # Merge relationship
                # If either node was a collision, we link to the collision node ID
                rel_query = """
                MATCH (s:Entity) WHERE s.id = $source_id OR s.name = $source
                MATCH (t:Entity) WHERE t.id = $target_id OR t.name = $target
                MERGE (s)-[r:FACT {predicate: $predicate}]->(t)
                ON CREATE SET
                    r.id = $id,
                    r.claim = $claim,
                    r.confidence = $confidence,
                    r.created_at = $created_at,
                    r.ttl_days = $ttl_days
                ON MATCH SET
                    r.confidence = (r.confidence + $confidence) / 2.0,
                    r.claim = r.claim + " | " + $claim
                RETURN r.id AS id
                """
                # Update degrees on nodes
                degree_query = """
                MATCH (s:Entity) WHERE s.id = $source_id OR s.name = $source
                MATCH (t:Entity) WHERE t.id = $target_id OR t.name = $target
                SET s.degree = s.degree + 1, t.degree = t.degree + 1
                """
                session.run(rel_query, 
                            source_id=source_id, target_id=target_id,
                            source=rel.source, target=rel.target,
                            predicate=rel.predicate, id=rel.id,
                            claim=rel.claim, confidence=rel.confidence,
                            created_at=rel.created_at, ttl_days=rel.ttl_days)
                session.run(degree_query, 
                            source_id=source_id, target_id=target_id,
                            source=rel.source, target=rel.target)
                results["merged_relationships"].append(f"{rel.source} -[{rel.predicate}]-> {rel.target}")

        return results

    def get_stale_relationships(self, threshold_days: int) -> List[Dict[str, Any]]:
        """Retrieves all relationships that are past their TTL duration in days."""
        if not self.verify_connection():
            return []
            
        # We fetch all facts and check the age in Python to avoid database-dependent datetime operations
        query = """
        MATCH (s:Entity)-[r:FACT]->(t:Entity)
        RETURN 
            r.id AS id, 
            s.name AS source, 
            t.name AS target, 
            r.predicate AS predicate, 
            r.claim AS claim, 
            r.confidence AS confidence, 
            r.created_at AS created_at, 
            r.ttl_days AS ttl_days
        """
        stale_list = []
        try:
            from datetime import datetime, timezone
            with self.driver.session(database=self.database) as session:
                res = session.run(query)
                for record in res:
                    created_at_str = record["created_at"]
                    ttl_days = record["ttl_days"] or 90
                    
                    if not created_at_str:
                        continue
                        
                    try:
                        # Parse ISO datetime
                        # Remove trailing Z if present for standard parsing
                        clean_str = created_at_str.replace("Z", "+00:00")
                        created_dt = datetime.fromisoformat(clean_str)
                        age_days = (datetime.now(timezone.utc) - created_dt).days
                        
                        if age_days >= threshold_days or age_days >= ttl_days:
                            stale_list.append({
                                "id": record["id"],
                                "source": record["source"],
                                "target": record["target"],
                                "predicate": record["predicate"],
                                "claim": record["claim"],
                                "confidence": record["confidence"],
                                "created_at": created_at_str,
                                "ttl_days": ttl_days,
                                "age_days": age_days
                            })
                    except Exception as date_err:
                        logger.warning(f"Error parsing date {created_at_str}: {date_err}")
                        
            logger.info(f"Temporal scan found {len(stale_list)} stale relationships.")
            return stale_list
        except Exception as e:
            logger.error(f"Failed to fetch stale relationships: {e}")
            return []

    def flag_stale(self, relationship_id: str):
        """Flags a relationship as stale in the database."""
        if not self.verify_connection():
            return
            
        query = """
        MATCH (s:Entity)-[r:FACT]->(t:Entity)
        WHERE r.id = $id
        SET r.stale = true, r.label = 'StaleContext'
        """
        try:
            with self.driver.session(database=self.database) as session:
                session.run(query, id=relationship_id)
            logger.info(f"Flagged relationship {relationship_id} as stale.")
        except Exception as e:
            logger.error(f"Failed to flag relationship {relationship_id} as stale: {e}")
