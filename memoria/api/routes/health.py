"""GET /api/health — system health check."""
import os
from fastapi import APIRouter
from dotenv import load_dotenv
load_dotenv()

router = APIRouter()


@router.get("/health")
async def health():
    db_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_status = "offline"
    try:
        from memoria.database.neo4j_client import Neo4jClient
        client = Neo4jClient(db_uri, os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "password"))
        if client.verify_connection():
            neo4j_status = "online"
        client.close()
    except Exception:
        pass

    return {
        "status": "ok",
        "neo4j": neo4j_status,
        "version": "1.0.0",
        "mode": "online" if neo4j_status == "online" else "demo"
    }
