import click
import os
import json
import time
from dotenv import load_dotenv

# Client and sub-modules
from .database.neo4j_client import Neo4jClient
from .parser.extraction import FactExtractor
from .embeddings import EmbeddingEngine
from .observability.tracker import MetricsTracker

load_dotenv()

@click.group()
def cli():
    """MemoriaAI: Adaptive Research Memory System CLI"""
    pass

@cli.command()
@click.option('--db-uri', default=os.getenv('NEO4J_URI', 'bolt://localhost:7687'), help='Neo4j connection URI')
@click.option('--db-user', default=os.getenv('NEO4J_USER', 'neo4j'), help='Neo4j username')
@click.option('--db-password', default=os.getenv('NEO4J_PASSWORD', 'password'), help='Neo4j password')
def dashboard(db_uri, db_user, db_password):
    """
    Displays the console observability metrics dashboard.
    """
    client = Neo4jClient(db_uri, db_user, db_password)
    from .observability.dashboard import ObservabilityDashboard
    dash = ObservabilityDashboard(client)
    dash.render()
    client.close()

@cli.command()
@click.argument('query')
@click.option('--db-uri', default=os.getenv('NEO4J_URI', 'bolt://localhost:7687'), help='Neo4j connection URI')
@click.option('--db-user', default=os.getenv('NEO4J_USER', 'neo4j'), help='Neo4j username')
@click.option('--db-password', default=os.getenv('NEO4J_PASSWORD', 'password'), help='Neo4j password')
@click.option('--json-output', is_flag=True, help='Print raw JSON dump')
def research(query, db_uri, db_user, db_password, json_output):
    """
    Executes an autonomous compilation sweep for a research query.
    """
    start_time = time.time()
    tracker = MetricsTracker()
    tracker.record_query()
    
    if not json_output:
        click.echo(f"Initializing autonomous research sweep for query: '{query}'")
    
    # 1. Connect to database
    client = Neo4jClient(db_uri, db_user, db_password)
    db_connected = False
    
    try:
        db_connected = client.verify_connection()
        if db_connected and not json_output:
            click.echo("Connected to Neo4j database.")
        elif not db_connected and not json_output:
            click.echo("Warning: Could not connect to Neo4j. Running in offline/fallback mode.")
    except Exception as e:
        if not json_output:
            click.echo(f"Warning: Connection error ({e}). Running in offline/fallback mode.")

    # Lazy imports
    from .ingestion.pipeline import IngestionPipeline
    from .query.hybrid_engine import HybridQueryEngine
    from .report.generator import ReportGenerator
    from .report.formatter import ReportFormatter
    from .memory.community_detector import CommunityDetector
    from .temporal.refresh_worker import PriorityQueueRefreshWorker
    from .temporal.decay import TemporalDecayEngine

    # Start the refresh worker if DB is connected
    refresh_worker = None
    if db_connected:
        try:
            client.initialize_vector_index()
            refresh_worker = PriorityQueueRefreshWorker(client)
            refresh_worker.start()
        except Exception as e:
            if not json_output:
                click.echo(f"Warning: Could not initialize refresh worker: {e}")

    # 2. Trigger web search and ingest fresh facts
    if not json_output:
        click.echo(f"Searching and ingesting fresh facts...")
        
    tracker.record_search()
    pipeline = IngestionPipeline(client)
    pipeline_res = pipeline.run(query, max_search_results=3)
    
    nodes_count = pipeline_res.get('extracted_nodes_count', 0)
    rels_count = pipeline_res.get('extracted_relationships_count', 0)
    
    if not json_output:
        click.echo(f"Ingestion finished. Extracted {nodes_count} nodes, {rels_count} relationships.")

    # 3. Query the hybrid memory graph
    if not json_output:
        click.echo("Querying hybrid memory graph...")
    query_engine = HybridQueryEngine(client)
    retrieval_res = query_engine.query(query)
    
    # Record queries to refresh worker to update query frequencies
    if refresh_worker and retrieval_res.get("entities"):
        for ent in retrieval_res["entities"]:
            refresh_worker.record_query(ent["name"])

    # 4. Check for stale relationships and queue refreshes
    if db_connected:
        try:
            decay_engine = TemporalDecayEngine(client)
            stale_rels = decay_engine.scan_for_stale(threshold_days=90)
            if stale_rels:
                tracker.increment("refresh_count", len(stale_rels))
                if refresh_worker:
                    if not json_output:
                        click.echo(f"Queuing {len(stale_rels)} stale claims for priority background refresh...")
                    for r in stale_rels:
                        refresh_worker.add_to_queue(r)
        except Exception as e:
            if not json_output:
                click.echo(f"Warning: Stale relationship check failed: {e}")

    # 5. Check and trigger community clustering
    if db_connected:
        try:
            comm_detector = CommunityDetector(client)
            comm_detector.check_and_trigger()
        except Exception as e:
            if not json_output:
                click.echo(f"Warning: Community detector check failed: {e}")

    # 6. Compile Report
    if not json_output:
        click.echo("Compiling research report...")
    report_generator = ReportGenerator(client)
    report = report_generator.generate(query, retrieval_res)
    
    # Track contradictions in report
    contradictions_count = len(report.divergence_contradiction_matrix.contradictions)
    # Don't count placeholder contradiction
    if contradictions_count == 1 and report.divergence_contradiction_matrix.contradictions[0].entity_or_relation == "None":
        contradictions_count = 0
    tracker.increment("contradiction_count", contradictions_count)

    # 7. Render Report
    formatter = ReportFormatter()
    formatter.render(report, json_output=json_output)

    # Clean up worker thread
    if refresh_worker:
        refresh_worker.stop()
        
    client.close()
    
    # Save latency
    latency_ms = (time.time() - start_time) * 1000.0
    tracker.record_latency(latency_ms)


@cli.command()
@click.option('--text', help='Raw text string to ingest')
@click.option('--file', help='Path to file containing text to ingest')
@click.option('--db-uri', default=os.getenv('NEO4J_URI', 'bolt://localhost:7687'), help='Neo4j connection URI')
@click.option('--db-user', default=os.getenv('NEO4J_USER', 'neo4j'), help='Neo4j username')
@click.option('--db-password', default=os.getenv('NEO4J_PASSWORD', 'password'), help='Neo4j password')
def ingest(text, file, db_uri, db_user, db_password):
    """
    Parses, embeds, and ingests facts from raw text or files into Neo4j with Memory Governance.
    """
    tracker = MetricsTracker()
    
    input_text = ""
    if text:
        input_text = text
    elif file:
        if not os.path.exists(file):
            click.echo(f"Error: File '{file}' not found.")
            return
        with open(file, 'r', encoding='utf-8') as f:
            input_text = f.read()
    else:
        click.echo("Error: Must specify either --text or --file.")
        return

    click.echo("1. Extracting factual triples and entities...")
    extractor = FactExtractor()
    payload = extractor.extract(input_text)
    
    click.echo(f"Extracted {len(payload.nodes)} nodes and {len(payload.relationships)} relationships.")

    if not payload.nodes:
        click.echo("No entities extracted. Ingestion terminated.")
        return

    click.echo("2. Generating local node embeddings (all-MiniLM-L6-v2)...")
    embedder = EmbeddingEngine()
    names = [node.name for node in payload.nodes]
    embeddings = embedder.get_embeddings(names)
    
    for node, emb in zip(payload.nodes, embeddings):
        node.embedding = emb

    click.echo("3. Ingesting into Neo4j with Memory Governance...")
    client = Neo4jClient(db_uri, db_user, db_password)
    if not client.verify_connection():
        click.echo("Warning: Could not connect to Neo4j. Showing ingestion payload instead of saving.")
        click.echo(json.dumps(payload.model_dump(exclude={"nodes": {"__all__": {"embedding"}}}), indent=2))
        client.close()
        
        # In offline mode, treat all relationships as accepted since we don't quality filter them
        tracker.increment("claims_accepted", len(payload.relationships))
        return

    try:
        # Initialize native vector index if connection succeeds
        client.initialize_vector_index()
        
        # 3.1 Entity Resolution
        from .memory.entity_resolver import EntityResolver
        resolver = EntityResolver(client)
        resolved_payload = resolver.resolve(payload)
        
        # 3.2 Ingest with Claim Versioning (which runs quality checks)
        from .memory.claim_versioning import ClaimVersioner
        versioner = ClaimVersioner(client)
        results = versioner.ingest_resolved_payload(resolved_payload, source_url="Manual CLI Ingest")
        
        # Track acceptance / rejection metrics
        accepted_count = results["created_versions"]
        rejected_count = len(payload.relationships) - accepted_count
        
        tracker.increment("claims_accepted", accepted_count)
        tracker.increment("claims_rejected", rejected_count)
        
        click.echo("\n--- Ingestion Summary ---")
        click.echo(f"Merged Nodes: {len(results['merged_nodes'])} ({', '.join(results['merged_nodes']) if results['merged_nodes'] else 'None'})")
        click.echo(f"Collision Nodes Routed to PotentialDuplicate Queue: {len(results['collision_nodes'])} ({', '.join(results['collision_nodes']) if results['collision_nodes'] else 'None'})")
        click.echo(f"Merged Relationships: {len(results['merged_relationships'])}")
        click.echo(f"Claim Versions Created: {results['created_versions']}")
        
    except Exception as e:
        click.echo(f"Error during database ingestion: {e}")
    finally:
        client.close()

if __name__ == '__main__':
    cli()
