"""Background job runner — executes research sweeps in a thread pool."""
import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
import os

load_dotenv()
logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=3)


def _run_research_sync(query: str) -> dict:
    """Runs the full research pipeline synchronously (called in thread)."""
    import time
    from memoria.database.neo4j_client import Neo4jClient
    from memoria.ingestion.pipeline import IngestionPipeline
    from memoria.query.hybrid_engine import HybridQueryEngine
    from memoria.report.generator import ReportGenerator

    db_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    db_user = os.getenv("NEO4J_USER", "neo4j")
    db_password = os.getenv("NEO4J_PASSWORD", "password")

    client = Neo4jClient(db_uri, db_user, db_password)
    db_connected = False
    try:
        db_connected = client.verify_connection()
    except Exception:
        pass

    try:
        pipeline = IngestionPipeline(client)
        ingest_stats = pipeline.run(query, max_search_results=3)

        if not db_connected:
            # We did the research (search + LLM extraction), but Neo4j is offline so we can't query the graph.
            # We return a dynamic report showing what we found in offline mode!
            return {
                "title": f"Research: {query} (No-Database Mode)",
                "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
                "executive_intelligence_matrix": {
                    "axioms": [
                        f"Successfully searched web and processed {len(ingest_stats.get('urls_processed', []))} sources.",
                        f"Extracted {ingest_stats.get('extracted_nodes_count', 0)} entities and {ingest_stats.get('extracted_relationships_count', 0)} claims.",
                        "Graph database is currently offline, so these facts were not saved and cannot be correlated."
                    ],
                    "fresh_variables": ingest_stats.get("urls_processed", [])
                },
                "factual_triple_trace": {"records": []},
                "divergence_contradiction_matrix": {"contradictions": []},
                "temporal_stability_indices": {"stabilities": []},
                "knowledge_gap_footprint": {"missing_structures": [
                    {"missing_entity": "Neo4j Database", "context": "Start Docker Desktop to enable memory persistence", "priority": "HIGH"}
                ]},
                "error": None
            }

        query_engine = HybridQueryEngine(client)
        retrieval_res = query_engine.query(query)

        report_gen = ReportGenerator(client)
        report = report_gen.generate(query, retrieval_res)
        return report.model_dump()
    except Exception as e:
        logger.error(f"Research error: {e}")
        # Return minimal fallback report
        return {
            "title": f"Research: {query}",
            "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
            "executive_intelligence_matrix": {
                "axioms": [f"Query '{query}' failed due to error: {e}"],
                "fresh_variables": []
            },
            "factual_triple_trace": {"records": []},
            "divergence_contradiction_matrix": {"contradictions": []},
            "temporal_stability_indices": {"stabilities": []},
            "knowledge_gap_footprint": {"missing_structures": []},
            "error": str(e)
        }
    finally:
        try:
            client.close()
        except Exception:
            pass


async def run_research_job(job_id: str, query: str):
    """Async wrapper — runs research in thread pool, updates job status."""
    from memoria.api.store import update_job, save_report

    await update_job(job_id, "running", "🔍 Searching web sources...")
    await asyncio.sleep(0.1)

    loop = asyncio.get_event_loop()
    try:
        await update_job(job_id, "running", "🧠 Extracting entities and claims...")
        result = await loop.run_in_executor(_executor, _run_research_sync, query)

        await update_job(job_id, "running", "💾 Saving report...")
        report_id = await save_report(query, result)
        result["report_id"] = report_id

        await update_job(job_id, "done", "✅ Complete", json.dumps(result))
        logger.info(f"Job {job_id} completed, report_id={report_id}")

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        await update_job(job_id, "failed", f"❌ Failed: {str(e)[:100]}")
