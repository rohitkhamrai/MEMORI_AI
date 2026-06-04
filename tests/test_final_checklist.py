import pytest
from unittest.mock import MagicMock, patch
import os
import json

from memoria.parser.cost_control import ClaimHashCache
from memoria.memory.quality import KnowledgeQualityManager
from memoria.query.graph_traversal import GraphTraverser
from memoria.observability.tracker import MetricsTracker
from memoria.schema import RelationshipEdge

def test_claim_hash_cache(tmp_path):
    """Test claim hash cache reads, writes, and md5 resolution."""
    cache_file = tmp_path / "test_cache.json"
    cache = ClaimHashCache(cache_path=str(cache_file))
    
    sentence = "LangGraph uses state objects."
    payload = {"nodes": [{"name": "LangGraph"}], "relationships": []}
    
    # Get on empty cache should return None
    assert cache.get(sentence) is None
    
    # Set cache
    cache.set(sentence, payload)
    
    # Reload and get
    new_cache = ClaimHashCache(cache_path=str(cache_file))
    result = new_cache.get(sentence)
    assert result is not None
    assert result["nodes"][0]["name"] == "LangGraph"

def test_knowledge_quality_manager():
    """Test memory importance scoring and low confidence rejection."""
    manager = KnowledgeQualityManager(confidence_floor=0.20, composite_floor=0.25)
    
    # Importance scoring: 0.4 * auth + 0.3 * freq + 0.2 * recency + 0.1 * centrality
    # 0.4*0.80 + 0.3*0.5 + 0.2*0.90 + 0.1*0.20 = 0.32 + 0.15 + 0.18 + 0.02 = 0.67
    assert manager.calculate_importance(source_authority=0.80, query_frequency=5, recency_score=0.90, degree=10) == 0.67
    
    # 0.4*0.95 + 0.3*1.0 + 0.2*0.80 + 0.1*1.00 = 0.38 + 0.30 + 0.16 + 0.10 = 0.94
    assert manager.calculate_importance(source_authority=0.95, query_frequency=12, recency_score=0.80, degree=60) == 0.94
    
    # Rejection: confidence < floor (0.20)
    rel_bad = RelationshipEdge(
        source="A", target="B", predicate="USES", claim="low confidence", confidence=0.15
    )
    assert manager.should_reject(rel_bad, source_score=0.95) is True
    
    # Rejection: composite < floor (0.25)
    # confidence 0.30 * source_score 0.50 = 0.15 (below 0.25)
    rel_weak = RelationshipEdge(
        source="A", target="B", predicate="USES", claim="weak composite", confidence=0.30
    )
    assert manager.should_reject(rel_weak, source_score=0.50) is True
    
    # Acceptable claim
    # confidence 0.80 * source_score 0.70 = 0.56 (above 0.25)
    rel_good = RelationshipEdge(
        source="A", target="B", predicate="USES", claim="strong claim", confidence=0.80
    )
    assert manager.should_reject(rel_good, source_score=0.70) is False

def test_bridge_entity_protection():
    """Test bridge entity identification and traversal protection."""
    mock_client = MagicMock()
    mock_client.verify_connection.return_value = True
    
    # Mock Neo4j session and record returns
    mock_session = MagicMock()
    mock_client.driver.session.return_value.__enter__.return_value = mock_session
    
    # Return count = 3 (connecting to 3 distinct communities)
    mock_record = MagicMock()
    mock_record.__getitem__.return_value = 3
    mock_session.run.return_value.single.return_value = mock_record
    
    traverser = GraphTraverser(mock_client)
    
    # Verify bridge identification
    assert traverser.is_bridge_entity("BridgeNode") is True
    
    # Verify that bridge degree count < 2 returns False
    mock_record_low = MagicMock()
    mock_record_low.__getitem__.return_value = 1
    mock_session.run.return_value.single.return_value = mock_record_low
    assert traverser.is_bridge_entity("RegularNode") is False

def test_metrics_tracker(tmp_path):
    """Test metrics logging and persistence."""
    metrics_file = tmp_path / "test_metrics.json"
    tracker = MetricsTracker(filepath=str(metrics_file))
    
    tracker.record_query()
    tracker.record_search()
    tracker.record_memory_hit()
    tracker.record_claim_status(accepted=True)
    tracker.record_claim_status(accepted=False)
    tracker.record_latency(250.0)
    
    summary = tracker.get_summary()
    assert summary["query_count"] == 1
    assert summary["search_count"] == 1
    assert summary["memory_hits"] == 1
    assert summary["average_latency_ms"] == 250.0
    assert summary["claim_acceptance_rate"] == 0.5
