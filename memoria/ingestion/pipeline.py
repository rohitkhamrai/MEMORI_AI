import logging
from typing import Dict, Any, List
from .web_fetcher import WebFetcher
from .search_engine import SearchEngine
from ..memory.source_scorer import SourceScorer
from ..parser.extraction import FactExtractor
from ..embeddings import EmbeddingEngine
from ..database.neo4j_client import Neo4jClient
from ..schema import IngestPayload

logger = logging.getLogger(__name__)

class IngestionPipeline:
    """Orchestrates web search, content fetching, fact extraction, source scoring, and DB ingestion."""
    
    def __init__(self, neo4j_client: Neo4jClient | None = None):
        self.search_engine = SearchEngine()
        self.web_fetcher = WebFetcher()
        self.source_scorer = SourceScorer()
        self.fact_extractor = FactExtractor()
        self.embedding_engine = EmbeddingEngine()
        self.neo4j_client = neo4j_client

    def run(self, query: str, max_search_results: int = 5) -> Dict[str, Any]:
        """Runs the ingestion pipeline end-to-end for a given query.
        
        Args:
            query: The research query/topic.
            max_search_results: Number of search results to crawl.
            
        Returns:
            Dict[str, Any]: Ingestion metrics and results.
        """
        logger.info(f"Starting ingestion pipeline for query: '{query}'")
        
        # 1. Search the web
        urls = self.search_engine.query(query, max_results=max_search_results)
        if not urls:
            logger.warning("No search results found.")
            return {"status": "no_results", "urls": []}
            
        total_nodes = 0
        total_relationships = 0
        processed_urls = []
        
        for url in urls:
            try:
                # 2. Fetch page content
                text = self.web_fetcher.fetch(url)
                if not text:
                    logger.info(f"Skipping empty or failed URL: {url}")
                    continue
                
                # 3. Score source credibility
                source_score = self.source_scorer.score_source(url, text)
                
                # 4. Extract facts (triples)
                payload: IngestPayload = self.fact_extractor.extract(text)
                
                # If no nodes/relationships extracted, skip
                if not payload.nodes and not payload.relationships:
                    logger.info(f"No facts extracted from: {url}")
                    continue
                
                logger.info(f"Extracted {len(payload.nodes)} nodes and {len(payload.relationships)} relationships from {url}")
                
                # 5. Apply source credibility score to relationship confidence values
                for edge in payload.relationships:
                    # Keep track of source url on edge (useful for versioning/audit)
                    edge.confidence = round(edge.confidence * source_score, 4)
                    # We store url inside claim description or metadata if schema supports it.
                    # Standard relationship model in schema.py:
                    # source, target, predicate, claim, confidence, created_at, ttl_days, id
                    # We can store source url in claim description if needed, or versioning handles it.
                    
                # 6. Embed nodes (if not already embedded)
                for node in payload.nodes:
                    if not node.embedding:
                        node.embedding = self.embedding_engine.get_embedding(f"{node.name} {node.description}")
                
                # 7. Ingest into Neo4j client (if client is active)
                if self.neo4j_client and self.neo4j_client.verify_connection():
                    # We import entity resolver locally to avoid circular dependencies
                    try:
                        from ..memory.entity_resolver import EntityResolver
                        resolver = EntityResolver(self.neo4j_client)
                        resolved_payload = resolver.resolve(payload)
                    except Exception as resolver_error:
                        logger.error(f"Entity resolution failed, falling back to raw payload: {resolver_error}")
                        resolved_payload = payload
                        
                    # Now ingest versioned/resolved payload
                    try:
                        from ..memory.claim_versioning import ClaimVersioner
                        versioner = ClaimVersioner(self.neo4j_client)
                        # ClaimVersioner will handle ingestion of claims using the new versioning schema
                        # Node ingestion still uses neo4j_client merging.
                        ingest_result = versioner.ingest_resolved_payload(resolved_payload, source_url=url)
                        logger.info(f"Ingested via ClaimVersioner: {ingest_result}")
                    except Exception as version_error:
                        logger.error(f"Claim versioner failed, falling back to raw client ingest: {version_error}")
                        self.neo4j_client.ingest_payload(resolved_payload)
                else:
                    logger.warning("Neo4jClient not connected or unavailable. Skipping DB ingestion.")
                    
                total_nodes += len(payload.nodes)
                total_relationships += len(payload.relationships)
                processed_urls.append(url)
                
            except Exception as e:
                logger.error(f"Error processing URL {url}: {e}", exc_info=True)
                
        return {
            "status": "success" if processed_urls else "failed",
            "urls_searched": urls,
            "urls_processed": processed_urls,
            "extracted_nodes_count": total_nodes,
            "extracted_relationships_count": total_relationships
        }
