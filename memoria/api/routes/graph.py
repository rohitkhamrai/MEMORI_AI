"""GET /api/graph — structured graph response with communities, hub nodes."""
import json
import os
from fastapi import APIRouter

router = APIRouter()

DEMO_GRAPH_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "demo_graph.json")


def _load_demo_graph() -> dict:
    with open(DEMO_GRAPH_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_neo4j_graph() -> dict:
    from memoria.database.neo4j_client import Neo4jClient
    client = Neo4jClient(
        os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        os.getenv("NEO4J_USER", "neo4j"),
        os.getenv("NEO4J_PASSWORD", "password")
    )
    if not client.verify_connection():
        raise Exception("offline")

    with client.driver.session() as s:
        node_rows = s.run(
            "MATCH (n:Entity) RETURN n.id AS id, n.name AS name, n.description AS description, "
            "n.degree AS degree, n.community_id AS community, n.importance AS importance LIMIT 100"
        ).data()
        edge_rows = s.run(
            "MATCH (a:Entity)-[r]->(b:Entity) RETURN a.id AS source, b.id AS target, "
            "type(r) AS predicate, r.confidence AS confidence LIMIT 200"
        ).data()
    client.close()

    nodes = [
        {
            "id": r.get("id", r.get("name", "")),
            "name": r.get("name", ""),
            "type": "ENTITY",
            "importance": float(r.get("importance") or 0.5),
            "community": int(r.get("community") or 0),
            "degree": int(r.get("degree") or 0),
            "description": r.get("description", "")
        }
        for r in node_rows
    ]
    edges = [
        {
            "source": r["source"],
            "target": r["target"],
            "predicate": r["predicate"],
            "confidence": float(r.get("confidence") or 0.8)
        }
        for r in edge_rows
    ]
    community_ids = list({n["community"] for n in nodes})
    colors = ["#6366f1", "#22d3ee", "#a78bfa", "#34d399", "#f59e0b", "#f87171", "#60a5fa"]
    communities = [{"id": cid, "color": colors[i % len(colors)], "size": sum(1 for n in nodes if n["community"] == cid)} for i, cid in enumerate(community_ids)]
    hub_nodes = [n["id"] for n in nodes if n.get("degree", 0) > 5]

    return {"nodes": nodes, "edges": edges, "communities": communities, "hub_nodes": hub_nodes}


@router.get("/graph")
async def graph():
    try:
        return _load_neo4j_graph()
    except Exception:
        return _load_demo_graph()
