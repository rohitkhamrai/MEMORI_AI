import logging
from datetime import datetime, timezone
from typing import Dict, Any, List
from ..schema import (
    CompiledResearchReport,
    ExecutiveIntelligenceMatrix,
    FactualTripleTrace,
    FactualTripleTraceRecord,
    DivergenceContradictionMatrix,
    DivergenceRecord,
    TemporalStabilityIndices,
    TemporalStabilityRecord,
    KnowledgeGapFootprint
)
from ..memory.contradiction_resolver import ContradictionResolver
from ..memory.knowledge_gap_detector import KnowledgeGapDetector
from ..temporal.decay import TemporalDecayEngine

logger = logging.getLogger(__name__)

class ReportGenerator:
    """Compiles fact retrieval, contradiction checks, decay indexing, and gaps into the 5-framework report."""
    
    def __init__(self, neo4j_client=None):
        self.client = neo4j_client
        self.contradiction_resolver = ContradictionResolver(neo4j_client)
        self.gap_detector = KnowledgeGapDetector(neo4j_client)

    def generate(self, query_text: str, retrieval_results: Dict[str, Any]) -> CompiledResearchReport:
        """Generates a complete CompiledResearchReport from search/query outputs.
        
        Args:
            query_text: User search query.
            retrieval_results: Output dictionary from HybridQueryEngine.query.
            
        Returns:
            CompiledResearchReport: The Pydantic structured research report.
        """
        entities = retrieval_results.get("entities", [])
        relationships = retrieval_results.get("relationships", [])
        
        # 1. Executive Intelligence Matrix
        # Axioms = high confidence (>= 0.70)
        # Fresh Variables = low confidence (< 0.70) or new
        axioms = []
        fresh_variables = []
        for rel in relationships:
            rel_desc = f"{rel['source']} -[{rel['predicate']}]-> {rel['target']} ('{rel['claim']}')"
            if rel.get("confidence", 0.0) >= 0.70:
                axioms.append(rel_desc)
            else:
                fresh_variables.append(rel_desc)
                
        # Keep clean defaults if empty
        if not axioms:
            axioms = ["No high-confidence axioms established in graph."]
        if not fresh_variables:
            fresh_variables = ["No fresh variables fetched."]

        # 2. Factual Triple Trace
        trace_records = []
        for rel in relationships:
            trace_records.append(FactualTripleTraceRecord(
                relationship_id=rel.get("id", "unknown"),
                source_name=rel["source"],
                target_name=rel["target"],
                predicate=rel["predicate"],
                confidence=rel.get("confidence", 0.5)
            ))

        # 3. Divergence & Contradiction Matrix
        # Resolve contradictions from retrieved relationships
        contradictions_resolved = self.contradiction_resolver.resolve(relationships)
        divergence_records = []
        for c in contradictions_resolved:
            sources = c["dominant_view"]["sources"] + [src for mv in c["minority_views"] for src in mv["sources"]]
            divergence_records.append(DivergenceRecord(
                entity_or_relation=c["entity_or_relation"],
                conflicting_sources=list(set(sources)),
                contradiction_summary=c["contradiction_summary"]
            ))
            
        if not divergence_records:
            divergence_records.append(DivergenceRecord(
                entity_or_relation="None",
                conflicting_sources=["None"],
                contradiction_summary="No contradictory claims detected in active context."
            ))

        # 4. Temporal Stability Indices
        stability_records = []
        for rel in relationships:
            created_at = rel.get("created_at")
            if created_at:
                try:
                    # Clean trailing Z for datetime parsing
                    clean_str = created_at.replace("Z", "+00:00")
                    created_dt = datetime.fromisoformat(clean_str)
                    age_seconds = (datetime.now(timezone.utc) - created_dt).total_seconds()
                    if age_seconds < 0:
                        age_seconds = 0
                except:
                    age_seconds = 86400.0  # Default 1 day in seconds
            else:
                age_seconds = 86400.0
                
            stability_index = TemporalDecayEngine.compute_stability_index(
                created_at or datetime.now(timezone.utc).isoformat(),
                ttl_days=rel.get("ttl_days", 90)
            )
            
            stability_records.append(TemporalStabilityRecord(
                entity_or_relation=f"{rel['source']} -[{rel['predicate']}]-> {rel['target']}",
                age_seconds=age_seconds,
                stability_index=stability_index
            ))

        # 5. Knowledge-Gap Footprint
        gap_footprint = self.gap_detector.detect(query_text, entities, relationships)

        return CompiledResearchReport(
            title=f"Autonomous Research Report: {query_text}",
            executive_intelligence_matrix=ExecutiveIntelligenceMatrix(
                axioms=axioms,
                fresh_variables=fresh_variables
            ),
            factual_triple_trace=FactualTripleTrace(records=trace_records),
            divergence_contradiction_matrix=DivergenceContradictionMatrix(contradictions=divergence_records),
            temporal_stability_indices=TemporalStabilityIndices(stabilities=stability_records),
            knowledge_gap_footprint=gap_footprint
        )
