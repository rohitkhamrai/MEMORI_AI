import queue
import threading
import logging
import time
from typing import Dict, Any, Optional
from ..database.neo4j_client import Neo4jClient
from .decay import TemporalDecayEngine

logger = logging.getLogger(__name__)

class PriorityQueueRefreshWorker:
    """Background worker that prioritizes and refreshes stale relationships using a Priority Queue."""
    
    def __init__(self, neo4j_client: Neo4jClient, IngestionPipelineClass=None):
        self.client = neo4j_client
        self.queue = queue.PriorityQueue()
        self.active = False
        self._thread: Optional[threading.Thread] = None
        self.IngestionPipelineClass = IngestionPipelineClass
        self.decay_engine = TemporalDecayEngine(neo4j_client)
        # In-memory registry to track query frequencies of entities
        self.query_frequencies: Dict[str, int] = {}

    def record_query(self, entity_name: str):
        """Records that an entity was queried, increasing its query frequency count."""
        self.query_frequencies[entity_name] = self.query_frequencies.get(entity_name, 0) + 1

    def calculate_priority(self, rel: Dict[str, Any]) -> float:
        """Calculates refresh priority score.
        
        Formula: Query Frequency * Centrality (degree) * (1 - Stability Index)
        """
        source = rel["source"]
        target = rel["target"]
        
        # Get query frequencies (default to 1)
        freq_s = self.query_frequencies.get(source, 1)
        freq_t = self.query_frequencies.get(target, 1)
        avg_freq = (freq_s + freq_t) / 2.0
        
        # Centrality (using degree property if available, else default to 2)
        # We can query node degrees or look up a cached value
        deg_s = rel.get("source_degree", 2)
        deg_t = rel.get("target_degree", 2)
        centrality = (deg_s + deg_t) / 2.0
        
        # Stability index
        created_at = rel["created_at"]
        ttl_days = rel.get("ttl_days", 90)
        stability = self.decay_engine.compute_stability_index(created_at, ttl_days)
        instability = 1.0 - stability
        
        # Priority Score
        priority = avg_freq * centrality * instability
        return priority

    def add_to_queue(self, rel: Dict[str, Any]):
        """Computes priority and pushes relationship onto the queue."""
        priority = self.calculate_priority(rel)
        # PriorityQueue in python pops lowest values first.
        # We store negative priority to pop highest priority first.
        item = (rel["id"], rel)
        self.queue.put((-priority, item))
        logger.info(f"Scheduled stale relationship refresh: {rel['source']} -[{rel['predicate']}]-> {rel['target']} (Priority: {priority:.2f})")

    def start(self):
        """Starts the background worker thread."""
        if self.active:
            return
        self.active = True
        self._thread = threading.Thread(target=self._worker_loop)
        self._thread.daemon = True
        self._thread.start()
        logger.info("PriorityQueueRefreshWorker background thread started.")

    def stop(self):
        """Stops the background worker thread."""
        self.active = False
        if self._thread:
            self._thread.join(timeout=2.0)
            logger.info("PriorityQueueRefreshWorker background thread stopped.")

    def _worker_loop(self):
        # Lazy import of IngestionPipeline to avoid circular reference
        pipeline = None
        
        while self.active:
            try:
                # Wait for an item with a timeout so we can exit loop if stopped
                try:
                    neg_priority, (rel_id, rel) = self.queue.get(timeout=2.0)
                except queue.Empty:
                    continue
                
                logger.info(f"Processing refresh for relationship: {rel['source']} -[{rel['predicate']}]-> {rel['target']}")
                
                # Fetch pipeline if not initialized
                if not pipeline:
                    if self.IngestionPipelineClass:
                        pipeline = self.IngestionPipelineClass(self.client)
                    else:
                        from ..ingestion.pipeline import IngestionPipeline
                        pipeline = IngestionPipeline(self.client)
                        
                # Perform targeted search to refresh claim
                search_query = f"{rel['source']} {rel['predicate']} {rel['target']}"
                logger.info(f"Refresh search query: '{search_query}'")
                
                # Execute pipeline (which does search, fetch, extraction, resolver, versioning)
                # Cap search results to 2 to minimize network / cost overhead during refreshes
                pipeline.run(search_query, max_search_results=2)
                
                # Clear stale flag in database after refresh
                self._clear_stale_flag(rel_id)
                
                self.queue.task_done()
                
                # Cooldown between refreshes
                time.sleep(5.0)
                
            except Exception as e:
                logger.error(f"Error in RefreshWorker loop: {e}", exc_info=True)
                time.sleep(5.0)

    def _clear_stale_flag(self, rel_id: str):
        if not self.client or not self.client.verify_connection():
            return
        query = """
        MATCH ()-[r:FACT]->()
        WHERE r.id = $id
        REMOVE r.stale, r.label
        """
        try:
            with self.client.driver.session(database=self.client.database) as session:
                session.run(query, id=rel_id)
            logger.info(f"Cleared stale flag for relationship {rel_id}.")
        except Exception as e:
            logger.error(f"Failed to clear stale flag for {rel_id}: {e}")
