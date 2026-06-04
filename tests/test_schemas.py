import pytest
from pydantic import ValidationError
from memoria.schema import EntityNode, RelationshipEdge, IngestPayload

def test_entity_node_validation():
    # Valid node
    node = EntityNode(
        name="LangGraph",
        aliases=["lang-graph", "Langchain Graph"],
        description="State management framework"
    )
    assert node.name == "LangGraph"
    assert len(node.id) > 0
    assert node.degree == 0

def test_relationship_edge_validation():
    # Valid relationship
    edge = RelationshipEdge(
        source="LangGraph",
        target="State Management",
        predicate="USES",
        claim="LangGraph leverages stateful actor graphs.",
        confidence=0.95
    )
    assert edge.predicate == "USES"
    assert edge.confidence == 0.95
    assert edge.ttl_days == 90

    # Invalid confidence
    with pytest.raises(ValidationError):
        RelationshipEdge(
            source="LangGraph",
            target="State Management",
            predicate="USES",
            claim="Invalid",
            confidence=1.5  # Must be <= 1.0
        )
