import logging
import re
from typing import List, Dict, Any, Set
from ..schema import KnowledgeGapRecord, KnowledgeGapFootprint

logger = logging.getLogger(__name__)

class KnowledgeGapDetector:
    """Identifies missing entities, unlinked relationships, or comparative gaps in retrieved knowledge."""
    
    def __init__(self, neo4j_client=None):
        self.client = neo4j_client

    def detect(self, query_text: str, retrieved_entities: List[Dict[str, Any]], retrieved_relationships: List[Dict[str, Any]]) -> KnowledgeGapFootprint:
        """Detects gaps in the retrieved subgraph and query context.
        
        Gaps classified as:
        1. Comparative Gaps: Entities mentioned in query but not connected.
        2. Isolated Nodes: Entities in the retrieved set with very low connection degrees.
        3. Missing Abstractions: Common entities missing standard relationships.
        """
        gaps: List[KnowledgeGapRecord] = []
        
        entity_names = {e["name"] for e in retrieved_entities}
        connected_pairs: Set[tuple[str, str]] = set()
        
        for rel in retrieved_relationships:
            s, t = rel["source"], rel["target"]
            connected_pairs.add((s, t))
            connected_pairs.add((t, s))

        # 1. Detect Comparative Gaps
        # Check if the query text mentions multiple entities that exist in the graph but aren't connected
        mentioned_entities = []
        for name in entity_names:
            # Simple word-boundary check for entity name in query
            if re.search(r'\b' + re.escape(name) + r'\b', query_text, re.IGNORECASE):
                mentioned_entities.append(name)
                
        if len(mentioned_entities) >= 2:
            for i in range(len(mentioned_entities)):
                for j in range(i + 1, len(mentioned_entities)):
                    ent_a = mentioned_entities[i]
                    ent_b = mentioned_entities[j]
                    
                    if (ent_a, ent_b) not in connected_pairs:
                        gaps.append(KnowledgeGapRecord(
                            missing_entity=f"{ent_a} <-> {ent_b}",
                            context=f"Query '{query_text}' mentions both '{ent_a}' and '{ent_b}', but they are not linked in the graph.",
                            priority="HIGH"
                        ))

        # 2. Detect Isolated / Low-Degree Nodes
        # Nodes that are matched but have degree <= 1 are weak points
        for ent in retrieved_entities:
            degree = ent.get("degree", 0)
            if degree <= 1:
                gaps.append(KnowledgeGapRecord(
                    missing_entity=ent["name"],
                    context=f"Entity '{ent['name']}' is matched but has low degree ({degree}). Needs neighborhood expansion.",
                    priority="MEDIUM"
                ))

        # 3. Look for comparative keywords in query (e.g. "vs", "compare", "difference")
        # and see if we have relationships matching comparative predicates
        is_comparative = any(kw in query_text.lower() for kw in ["vs", "versus", "compare", "comparison", "difference"])
        if is_comparative and len(entity_names) > 0:
            has_comparison_edge = False
            for rel in retrieved_relationships:
                pred = rel["predicate"].upper()
                if "COMPARE" in pred or "VS" in pred or "DIFFER" in pred or "RELATE" in pred:
                    has_comparison_edge = True
                    break
            
            if not has_comparison_edge and len(entity_names) >= 2:
                gaps.append(KnowledgeGapRecord(
                    missing_entity="Comparative Relationship",
                    context=f"Query requests comparison, but no comparative relationships exist between retrieved entities.",
                    priority="HIGH"
                ))

        # If no gaps found, add a low-priority placeholder to keep report structure valid
        if not gaps:
            gaps.append(KnowledgeGapRecord(
                missing_entity="None",
                context="All retrieved entities are well-integrated. No obvious knowledge gaps found.",
                priority="LOW"
            ))

        return KnowledgeGapFootprint(missing_structures=gaps)
