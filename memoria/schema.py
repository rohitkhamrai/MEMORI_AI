from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime, timezone
import uuid

class EntityNode(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="UUID v4 Seed")
    name: str = Field(..., description="Normalized Lexical Form, e.g., 'LangGraph'")
    aliases: List[str] = Field(default_factory=list, description="Alternative Lexical Keys / Edge Aliases")
    description: str = Field(..., description="Synthesized System Context Summary")
    embedding: Optional[List[float]] = Field(None, description="Dimensions: 384 via bge-small-en")
    degree: int = Field(0, description="Global Node Edge Connection Tally")
    community_id: Optional[int] = Field(None, description="Leiden Topological Structural Domain ID")
    last_updated: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        description="ISO 8601 UTC Zulu Standard"
    )

class RelationshipEdge(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="UUID v4 Verification Tracer")
    source: str = Field(..., description="EntityNode.id (Root Node Mapping Pointer) or EntityNode.name")
    target: str = Field(..., description="EntityNode.id (Terminal Node Mapping Pointer) or EntityNode.name")
    predicate: str = Field(..., description="Normalized Operational Verb Token, e.g., 'SUPPORTS'")
    claim: str = Field(..., description="Raw Unparsed Source Context Semantic Segment")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Computed Truth Integrity Index: 0.00 - 1.00")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        description="Ingestion Tracking Date Record"
    )
    ttl_days: int = Field(90, description="Temporal Decay Horizon Frame Threshold; Default: 90")

class IngestPayload(BaseModel):
    nodes: List[EntityNode] = Field(default_factory=list)
    relationships: List[RelationshipEdge] = Field(default_factory=list)

# Report schemas as defined in Section 2 of Compiled Deliverable Report Artifacts

class ExecutiveIntelligenceMatrix(BaseModel):
    axioms: List[str] = Field(..., description="Established graph axioms")
    fresh_variables: List[str] = Field(..., description="Freshly integrated variables")

class FactualTripleTraceRecord(BaseModel):
    relationship_id: str
    source_name: str
    target_name: str
    predicate: str
    confidence: float

class FactualTripleTrace(BaseModel):
    records: List[FactualTripleTraceRecord] = Field(..., description="Open logging record of triples used")

class DivergenceRecord(BaseModel):
    entity_or_relation: str
    conflicting_sources: List[str]
    contradiction_summary: str

class DivergenceContradictionMatrix(BaseModel):
    contradictions: List[DivergenceRecord] = Field(..., description="Callouts of conflicting source links")

class TemporalStabilityRecord(BaseModel):
    entity_or_relation: str
    age_seconds: float
    stability_index: float  # e^(-age/ttl)

class TemporalStabilityIndices(BaseModel):
    stabilities: List[TemporalStabilityRecord] = Field(..., description="Real-time accuracy and truth-security values")

class KnowledgeGapRecord(BaseModel):
    missing_entity: str
    context: str
    priority: str  # e.g., 'HIGH', 'MEDIUM', 'LOW'

class KnowledgeGapFootprint(BaseModel):
    missing_structures: List[KnowledgeGapRecord] = Field(..., description="Technical index mapping unverified variables or missing nodes")

class CompiledResearchReport(BaseModel):
    title: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
    executive_intelligence_matrix: ExecutiveIntelligenceMatrix
    factual_triple_trace: FactualTripleTrace
    divergence_contradiction_matrix: DivergenceContradictionMatrix
    temporal_stability_indices: TemporalStabilityIndices
    knowledge_gap_footprint: KnowledgeGapFootprint
