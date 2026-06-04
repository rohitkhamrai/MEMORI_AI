import pytest
from click.testing import CliRunner
from memoria.embeddings import EmbeddingEngine
from memoria.parser.extraction import FactExtractor
from memoria.cli import cli

def test_embedding_engine():
    engine = EmbeddingEngine()
    emb = engine.get_embedding("Test node")
    
    assert isinstance(emb, list)
    assert len(emb) == 384
    assert all(isinstance(x, float) for x in emb)

    # Test batch embedding
    embs = engine.get_embeddings(["First", "Second"])
    assert len(embs) == 2
    assert len(embs[0]) == 384
    assert len(embs[1]) == 384

def test_fact_extractor_heuristics():
    extractor = FactExtractor()
    # Force heuristic mode by clearing API key just for this test
    original_key = extractor.api_key
    extractor.api_key = None
    
    text = "LangGraph uses state-centric actor models. CrewAI coordinates agents."
    payload = extractor.extract(text)
    
    assert len(payload.nodes) >= 2
    assert len(payload.relationships) >= 2
    
    node_names = [n.name for n in payload.nodes]
    assert "LangGraph" in node_names
    assert "state-centric actor models" in node_names
    assert "CrewAI" in node_names
    assert "agents" in node_names

    predicates = [r.predicate for r in payload.relationships]
    assert "USES" in predicates
    assert "COORDINATES" in predicates

    # Restore key
    extractor.api_key = original_key

def test_cli_ingest_command_offline():
    runner = CliRunner()
    result = runner.invoke(cli, [
        "ingest",
        "--text",
        "LangGraph uses state-centric actor models."
    ])
    
    assert result.exit_code == 0
    assert "Extracting factual triples and entities..." in result.output
    assert "Generating local node embeddings" in result.output
    assert "Warning: Could not connect to Neo4j. Showing ingestion payload instead of saving." in result.output
    assert "LangGraph" in result.output
    assert "USES" in result.output
