import pytest
from memoria.router import CognitiveMaturityRouter, MaturityStage

def test_router_stages():
    # Stage 0 Bootstrap: 0 - 1,000
    assert CognitiveMaturityRouter.get_stage(0) == MaturityStage.BOOTSTRAP
    assert CognitiveMaturityRouter.get_stage(500) == MaturityStage.BOOTSTRAP
    assert CognitiveMaturityRouter.get_stage(999) == MaturityStage.BOOTSTRAP

    # Stage 1 Sparse: 1,000 - 5,000
    assert CognitiveMaturityRouter.get_stage(1000) == MaturityStage.SPARSE
    assert CognitiveMaturityRouter.get_stage(3000) == MaturityStage.SPARSE
    assert CognitiveMaturityRouter.get_stage(4999) == MaturityStage.SPARSE

    # Stage 2 Structured: 5,000 - 50,000
    assert CognitiveMaturityRouter.get_stage(5000) == MaturityStage.STRUCTURED
    assert CognitiveMaturityRouter.get_stage(25000) == MaturityStage.STRUCTURED
    assert CognitiveMaturityRouter.get_stage(49999) == MaturityStage.STRUCTURED

    # Stage 3 Cognitive: 50,000+
    assert CognitiveMaturityRouter.get_stage(50000) == MaturityStage.COGNITIVE
    assert CognitiveMaturityRouter.get_stage(1000000) == MaturityStage.COGNITIVE

def test_router_invalid_values():
    with pytest.raises(ValueError):
        CognitiveMaturityRouter.get_stage(-1)

def test_routing_strategy_weights():
    bootstrap_strat = CognitiveMaturityRouter.get_routing_strategy(100)
    assert bootstrap_strat.vector_weight == 0.80
    assert bootstrap_strat.graph_weight == 0.00

    sparse_strat = CognitiveMaturityRouter.get_routing_strategy(2000)
    assert sparse_strat.vector_weight == 0.60
    assert sparse_strat.graph_weight == 0.25

    structured_strat = CognitiveMaturityRouter.get_routing_strategy(15000)
    assert structured_strat.vector_weight == 0.40
    assert structured_strat.graph_weight == 0.40

    cognitive_strat = CognitiveMaturityRouter.get_routing_strategy(80000)
    assert cognitive_strat.vector_weight == 0.00
    assert cognitive_strat.graph_weight == 0.60
