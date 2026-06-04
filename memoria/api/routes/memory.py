"""Memory Explorer API — entities, claims, contradictions."""
import os
from fastapi import APIRouter, Query

router = APIRouter()


def _get_demo_entities():
    import json
    path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "demo_graph.json")
    with open(path, "r", encoding="utf-8") as f:
        g = json.load(f)
    entities = []
    for n in g["nodes"]:
        entities.append({
            "id": n["id"],
            "name": n["name"],
            "type": n["type"],
            "importance": n["importance"],
            "community": n["community"],
            "degree": n["degree"],
            "description": n["description"],
            "source_authority": round(n["importance"] * 0.95, 2),
            "last_verified": "2025-06-01T12:00:00Z",
            "claim_count": n["degree"] * 2
        })
    return entities


def _get_demo_claims():
    import json
    path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "demo_graph.json")
    with open(path, "r", encoding="utf-8") as f:
        g = json.load(f)
    # Build name map
    name_map = {n["id"]: n["name"] for n in g["nodes"]}
    claims = []
    for i, e in enumerate(g["edges"]):
        claims.append({
            "id": f"claim_{i+1:03d}",
            "source": name_map.get(e["source"], e["source"]),
            "target": name_map.get(e["target"], e["target"]),
            "predicate": e["predicate"],
            "confidence": e["confidence"],
            "version": 1,
            "status": "verified" if e["confidence"] > 0.85 else "pending",
            "created_at": "2025-06-01T10:00:00Z"
        })
    return claims


def _get_demo_contradictions():
    return [
        {
            "id": "contra_001",
            "entity": "GPT-4",
            "conflicting_claims": ["GPT-4 IS_SUBSET_OF GPT-3 (conf 0.51)", "GPT-4 SUPERSEDES GPT-3 (conf 0.96)"],
            "resolution": "UNRESOLVED",
            "priority": "HIGH"
        },
        {
            "id": "contra_002",
            "entity": "Python",
            "conflicting_claims": ["Python IS_FASTER_THAN JavaScript (conf 0.40)", "Python IS_SLOWER_THAN JavaScript (conf 0.88)"],
            "resolution": "PENDING_REVIEW",
            "priority": "MEDIUM"
        }
    ]


@router.get("/memory/entities")
async def get_entities(limit: int = Query(50, ge=1, le=200)):
    try:
        from memoria.database.neo4j_client import Neo4jClient
        client = Neo4jClient(
            os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            os.getenv("NEO4J_USER", "neo4j"),
            os.getenv("NEO4J_PASSWORD", "password")
        )
        if not client.verify_connection():
            raise Exception("offline")
        with client.driver.session() as s:
            rows = s.run(
                f"MATCH (n:Entity) RETURN n.id AS id, n.name AS name, n.description AS description, "
                f"n.degree AS degree, n.importance AS importance, n.community_id AS community LIMIT {limit}"
            ).data()
        client.close()
        return {"entities": rows, "source": "neo4j"}
    except Exception:
        entities = _get_demo_entities()[:limit]
        return {"entities": entities, "source": "demo"}


@router.get("/memory/claims")
async def get_claims(limit: int = Query(50, ge=1, le=200)):
    try:
        from memoria.database.neo4j_client import Neo4jClient
        client = Neo4jClient(
            os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            os.getenv("NEO4J_USER", "neo4j"),
            os.getenv("NEO4J_PASSWORD", "password")
        )
        if not client.verify_connection():
            raise Exception("offline")
        with client.driver.session() as s:
            rows = s.run(
                f"MATCH (a)-[r]->(b) RETURN a.name AS source, b.name AS target, type(r) AS predicate, "
                f"r.confidence AS confidence, r.created_at AS created_at LIMIT {limit}"
            ).data()
        client.close()
        return {"claims": rows, "source": "neo4j"}
    except Exception:
        claims = _get_demo_claims()[:limit]
        return {"claims": claims, "source": "demo"}


@router.get("/memory/contradictions")
async def get_contradictions():
    try:
        from memoria.database.neo4j_client import Neo4jClient
        client = Neo4jClient(
            os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            os.getenv("NEO4J_USER", "neo4j"),
            os.getenv("NEO4J_PASSWORD", "password")
        )
        if not client.verify_connection():
            raise Exception("offline")
        with client.driver.session() as s:
            # Look for nodes marked as PotentialCollision
            rows = s.run(
                "MATCH (n:PotentialCollision) RETURN n.id AS id, n.name AS entity, 'UNRESOLVED' AS resolution, 'HIGH' AS priority LIMIT 50"
            ).data()
        client.close()
        
        # If Neo4j is online but no collisions found, return empty array instead of demo data
        if not rows:
            return {"contradictions": [], "source": "neo4j"}
            
        return {"contradictions": rows, "source": "neo4j"}
    except Exception:
        return {"contradictions": _get_demo_contradictions(), "source": "demo"}

