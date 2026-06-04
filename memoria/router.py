from enum import Enum
from typing import NamedTuple

class MaturityStage(Enum):
    BOOTSTRAP = "Bootstrap"
    SPARSE = "Sparse"
    STRUCTURED = "Structured"
    COGNITIVE = "Cognitive"

class RoutingStrategy(NamedTuple):
    stage: MaturityStage
    min_triples: int
    max_triples: int
    vector_weight: float
    graph_weight: float
    description: str

# Defined by Cognitive Maturity Lifecycle Roadmap
STRATEGIES = {
    MaturityStage.BOOTSTRAP: RoutingStrategy(
        stage=MaturityStage.BOOTSTRAP,
        min_triples=0,
        max_triples=1000,
        vector_weight=0.80,
        graph_weight=0.00,  # 80% Vector Allocation, rest is logging/noise
        description="Topology yields purely noise. System functions as structural logging ledger. Context leans on embedding layers."
    ),
    MaturityStage.SPARSE: RoutingStrategy(
        stage=MaturityStage.SPARSE,
        min_triples=1000,
        max_triples=5000,
        vector_weight=0.60,
        graph_weight=0.25,  # 60% Vec / 25% Graph
        description="Shallow 1-hop path queries begin actively informing semantic routing. Nearest-neighbor pairs drive context mapping."
    ),
    MaturityStage.STRUCTURED: RoutingStrategy(
        stage=MaturityStage.STRUCTURED,
        min_triples=5000,
        max_triples=50000,
        vector_weight=0.40,
        graph_weight=0.40,  # Balanced Engine (40% Graph / 40% Vec)
        description="Triggers background Louvain/Leiden tasks. Hydrates structural degree indices and deploys dynamic hub filters."
    ),
    MaturityStage.COGNITIVE: RoutingStrategy(
        stage=MaturityStage.COGNITIVE,
        min_triples=50000,
        max_triples=float('inf'),
        vector_weight=0.00,  # Embeddings localized for syntax checking. 60% Pure Topology
        graph_weight=0.60,
        description="Graph behaves as deterministic reality standard. Embeddings localized for syntax checking. Web updates strictly for validation."
    )
}

class CognitiveMaturityRouter:
    @staticmethod
    def get_stage(triple_count: int) -> MaturityStage:
        if triple_count < 0:
            raise ValueError("Triple count cannot be negative")
        
        for stage, strategy in STRATEGIES.items():
            if strategy.min_triples <= triple_count < strategy.max_triples:
                return stage
        return MaturityStage.COGNITIVE

    @classmethod
    def get_routing_strategy(cls, triple_count: int) -> RoutingStrategy:
        stage = cls.get_stage(triple_count)
        return STRATEGIES[stage]
