import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class ContradictionResolver:
    """Detects and resolves conflicting claims inside the memory graph."""
    
    def __init__(self, neo4j_client=None):
        self.client = neo4j_client

    def resolve(self, relationships: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identifies conflicting relationships and partitions them into Dominant and Minority views.
        
        Args:
            relationships: List of relationships (as dictionaries) retrieved during query.
            
        Returns:
            List[Dict[str, Any]]: List of contradiction records with resolution metrics.
        """
        # Group relationships by (source, predicate)
        groups: Dict[tuple[str, str], List[Dict[str, Any]]] = {}
        for rel in relationships:
            key = (rel["source"], rel["predicate"])
            groups.setdefault(key, []).append(rel)

        resolved_contradictions = []

        for (source, predicate), edges in groups.items():
            # If all point to the same target and have similar claims, no contradiction
            # But if there are different targets for the same predicate, it might be a conflict
            if len(edges) <= 1:
                continue
                
            # Check if targets differ or if claims differ significantly
            targets = {e["target"] for e in edges}
            if len(targets) <= 1:
                # Same target, check if claim texts look contradictory (not common for exact same target/predicate)
                continue
                
            # We have a contradiction! Multiple distinct targets for the same (source, predicate)
            logger.info(f"Contradiction detected for ({source}, {predicate}) pointing to targets: {targets}")
            
            # Sort edges by confidence descending
            sorted_edges = sorted(edges, key=lambda x: x["confidence"], reverse=True)
            dominant = sorted_edges[0]
            minorities = sorted_edges[1:]
            
            # Calculate consensus confidence
            dominant_conf = dominant["confidence"]
            max_minority_conf = minorities[0]["confidence"] if minorities else 0.0
            
            # Consensus degree = dominant_conf - max_minority_conf
            consensus_confidence = round(dominant_conf - max_minority_conf, 4)
            
            # Fetch sources of versions from DB if client is active
            dominant_sources = self._get_version_sources(dominant.get("id"))
            minority_sources = []
            for m in minorities:
                minority_sources.extend(self._get_version_sources(m.get("id")))

            resolved_contradictions.append({
                "entity_or_relation": f"{source} -[{predicate}]-> ...",
                "dominant_view": {
                    "target": dominant["target"],
                    "claim": dominant["claim"],
                    "confidence": dominant_conf,
                    "sources": dominant_sources
                },
                "minority_views": [
                    {
                        "target": m["target"],
                        "claim": m["claim"],
                        "confidence": m["confidence"],
                        "sources": self._get_version_sources(m.get("id"))
                    } for m in minorities
                ],
                "consensus_confidence": consensus_confidence,
                "contradiction_summary": f"Dominant: '{dominant['target']}' (conf: {dominant_conf}) vs Minority: '{[m['target'] for m in minorities]}' (conf: {max_minority_conf})"
            })

        return resolved_contradictions

    def _get_version_sources(self, rel_id: str | None) -> List[str]:
        """Helper to get source URLs for a relationship's versions from Neo4j."""
        if not rel_id or not self.client or not self.client.verify_connection():
            return ["Web Ingestion Pipeline (cached)"]
            
        query = """
        MATCH (v:ClaimVersion)
        WHERE v.id = $rel_id OR (v)-[:HAS_VERSION]-(:Entity) // Linkage trace
        RETURN v.source_url AS source_url
        """
        # Alternatively query by HAS_VERSION rel
        query_rel = """
        MATCH (s:Entity)-[h:HAS_VERSION]->(v:ClaimVersion)
        WHERE h.rel_id = $rel_id
        RETURN DISTINCT v.source_url AS source_url
        """
        try:
            with self.client.driver.session(database=self.client.database) as session:
                res = session.run(query_rel, rel_id=rel_id)
                urls = [record["source_url"] for record in res if record["source_url"]]
                return urls if urls else ["Web Ingestion"]
        except Exception as e:
            logger.debug(f"Failed to fetch version sources for relationship {rel_id}: {e}")
            return ["Web Ingestion"]
