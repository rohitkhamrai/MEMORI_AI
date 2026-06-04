import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
import math

from memoria.ingestion.search_engine import SearchEngine, DuckDuckGoProvider, BraveProvider
from memoria.memory.source_scorer import SourceScorer
from memoria.memory.contradiction_resolver import ContradictionResolver
from memoria.memory.knowledge_gap_detector import KnowledgeGapDetector
from memoria.memory.entity_resolver import EntityResolver
from memoria.memory.claim_versioning import ClaimVersioner
from memoria.temporal.refresh_worker import PriorityQueueRefreshWorker
from memoria.schema import EntityNode, RelationshipEdge, IngestPayload

def test_search_engine_fallback():
    """Verify search engine priority selection and fallbacks."""
    with patch.dict("os.environ", {"TAVILY_API_KEY": "tavily_mock_key"}):
        engine = SearchEngine()
        # Should have TavilyProvider first, then DuckDuckGoProvider
        assert len(engine.providers) == 2
        assert engine.providers[0].__class__.__name__ == "TavilyProvider"
        assert engine.providers[1].__class__.__name__ == "DuckDuckGoProvider"

def test_source_scorer():
    """Verify credibility scoring, recency decay, and agreement math."""
    scorer = SourceScorer()
    
    # Authority buckets
    assert scorer.get_domain_authority("https://docs.crewai.com/index.html") == 0.95
    assert scorer.get_domain_authority("https://arxiv.org/abs/2304.12345") == 0.90
    assert scorer.get_domain_authority("https://medium.com/some-post") == 0.70
    assert scorer.get_domain_authority("https://randomblog.com/post") == 0.35
    
    # Recency decay
    url_fresh = "https://blog.com/2026/06/01/post"
    # Overwrite the base time for test stability
    with patch('memoria.memory.source_scorer.datetime') as mock_date:
        # datetime.now() returns June 3, 2026
        mock_date.now.return_value = datetime(2026, 6, 3)
        mock_date.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        # Fresh: 2 days old -> very close to 1.0
        decay = scorer.get_recency_decay(url_fresh)
        assert decay > 0.90
        
        # Stale: 1 year old -> e^(-365/365) = e^-1 approx 0.36
        url_stale = "https://blog.com/2025/06/03/post"
        decay_stale = scorer.get_recency_decay(url_stale)
        assert pytest.approx(decay_stale, 0.05) == math.exp(-1)

    # Cross-source agreement
    # 1 - (1 - 0.70) * (1 - 0.70) = 1 - 0.09 = 0.91
    assert scorer.combine_confidences([0.70, 0.70]) == 0.91
    assert scorer.combine_confidences([0.50]) == 0.50
    assert scorer.combine_confidences([]) == 0.0

def test_contradiction_resolver():
    """Verify contradiction detection identifies dominant and minority views."""
    resolver = ContradictionResolver()
    
    # Scenario: s -> predicate -> t1 (high confidence) vs t2 (low confidence)
    rels = [
        {
            "id": "rel-1",
            "source": "LangGraph",
            "target": "StateObject",
            "predicate": "USES_STATE_MODEL",
            "claim": "LangGraph state management is based on a central StateObject.",
            "confidence": 0.90,
            "created_at": "2026-06-03T12:00:00Z"
        },
        {
            "id": "rel-2",
            "source": "LangGraph",
            "target": "ThreadDict",
            "predicate": "USES_STATE_MODEL",
            "claim": "LangGraph uses simple thread-specific dictionaries for state.",
            "confidence": 0.40,
            "created_at": "2026-06-03T12:00:00Z"
        }
    ]
    
    resolved = resolver.resolve(rels)
    assert len(resolved) == 1
    record = resolved[0]
    
    assert record["dominant_view"]["target"] == "StateObject"
    assert record["dominant_view"]["confidence"] == 0.90
    assert record["minority_views"][0]["target"] == "ThreadDict"
    assert record["minority_views"][0]["confidence"] == 0.40
    assert record["consensus_confidence"] == 0.50

def test_knowledge_gap_detector():
    """Verify gap detector flags unlinked entity co-occurrences."""
    detector = KnowledgeGapDetector()
    
    retrieved_entities = [
        {"name": "LangGraph", "degree": 5},
        {"name": "CrewAI", "degree": 6}
    ]
    
    # Query mentions both but no relationship connects them
    query = "Compare LangGraph vs CrewAI orchestration models"
    retrieved_relationships = []
    
    gaps = detector.detect(query, retrieved_entities, retrieved_relationships)
    
    assert len(gaps.missing_structures) >= 1
    # Check that high priority gap is registered for comparative pair
    assert any(g.priority == "HIGH" and "LangGraph" in g.missing_entity and "CrewAI" in g.missing_entity for g in gaps.missing_structures)

def test_priority_queue_refresh_worker_scoring():
    """Verify refresh worker priority sorting logic."""
    mock_client = MagicMock()
    mock_client.verify_connection.return_value = True
    
    worker = PriorityQueueRefreshWorker(mock_client)
    
    # Record query count to increase frequency
    worker.record_query("LangGraph")
    worker.record_query("LangGraph") # frequency = 2
    
    rel_stale = {
        "id": "stale-rel-id",
        "source": "LangGraph",
        "target": "State",
        "predicate": "USES",
        "claim": "LangGraph uses State",
        "confidence": 0.50,
        "created_at": "2024-06-03T12:00:00Z", # highly decayed
        "ttl_days": 90,
        "source_degree": 10,
        "target_degree": 2
    }
    
    priority = worker.calculate_priority(rel_stale)
    assert priority > 0.0
    
    # Push to queue
    worker.add_to_queue(rel_stale)
    assert not worker.queue.empty()
    
    prio_val, (item_id, item) = worker.queue.get()
    assert item_id == "stale-rel-id"
    # Negative priority value because Python PQ is min-heap
    assert prio_val == -priority

def test_entity_resolver_collision():
    """Verify entity resolver detects namespace collisions."""
    mock_client = MagicMock()
    mock_client.verify_connection.return_value = True
    
    # Stub check_structural_connection to return 0.0 (no overlap = collision)
    mock_client.check_structural_connection.return_value = 0.0
    
    resolver = EntityResolver(mock_client)
    
    # Mock finding a node with high similarity
    resolver.find_similar_existing_nodes = MagicMock(return_value=[{
        "id": "node-existing-123",
        "name": "State",
        "aliases": [],
        "score": 0.90  # High similarity
    }])
    
    node = EntityNode(
        id="new-node-uuid",
        name="State",
        description="Incoming different definition of State.",
    )
    
    # Dummy relationship to trigger structural connection check
    payload = IngestPayload(
        nodes=[node],
        relationships=[RelationshipEdge(
            source="State",
            target="DifferentModule",
            predicate="DEFINES",
            claim="State defines DifferentModule",
            confidence=0.80
        )]
    )
    
    resolved = resolver.resolve(payload)
    
    # Name should be modified to include collision label
    resolved_node = resolved.nodes[0]
    assert resolved_node.name.startswith("State (Collision")
    assert resolved_node.id.startswith("collision-")
