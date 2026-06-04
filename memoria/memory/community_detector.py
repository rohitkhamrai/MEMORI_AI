import logging
import threading
import networkx as nx
import community as community_louvain
from ..database.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)

class CommunityDetector:
    """Manages Leiden/Louvain community detection and partition assignment in Neo4j."""
    
    def __init__(self, neo4j_client: Neo4jClient):
        self.client = neo4j_client
        self._lock = threading.Lock()

    def get_metadata(self) -> tuple[int, int]:
        """Gets current triple count and the count during the last clustering run.
        
        Returns:
            tuple[int, int]: (current_count, last_run_count)
        """
        if not self.client or not self.client.verify_connection():
            return 0, 0
            
        current_count = self.client.get_triple_count()
        
        last_run_count = 0
        query = "MATCH (m:GraphMetadata) RETURN m.last_clustering_count AS last_count"
        try:
            with self.client.driver.session(database=self.client.database) as session:
                res = session.run(query)
                record = res.single()
                if record and record["last_count"] is not None:
                    last_run_count = record["last_count"]
        except Exception as e:
            logger.debug(f"Metadata node not found or failed to read: {e}")
            
        return current_count, last_run_count

    def update_metadata(self, count: int):
        """Updates the last clustering run count in database metadata."""
        query = """
        MERGE (m:GraphMetadata)
        SET m.last_clustering_count = $count, m.last_clustering_time = datetime()
        """
        try:
            with self.client.driver.session(database=self.client.database) as session:
                session.run(query, count=count)
        except Exception as e:
            logger.error(f"Failed to update GraphMetadata: {e}")

    def check_and_trigger(self) -> bool:
        """Checks if community detection should run based on new triple count thresholds."""
        current_count, last_run_count = self.get_metadata()
        logger.info(f"Community Detection check: current triples = {current_count}, last run = {last_run_count}")
        
        # Trigger conditions:
        # 1. No clustering has ever run, and we have crossed 5,000 triples
        # 2. We have added 10,000+ new triples since the last run
        if last_run_count == 0 and current_count >= 5000:
            logger.info("First maturity threshold (5,000 triples) crossed. Triggering Louvain clustering...")
            self.trigger_async()
            return True
        elif last_run_count > 0 and (current_count - last_run_count) >= 10000:
            logger.info(f"Periodic threshold (10,000 delta) crossed since {last_run_count}. Triggering Louvain...")
            self.trigger_async()
            return True
            
        return False

    def trigger_async(self):
        """Launches the community detection job in a background thread."""
        thread = threading.Thread(target=self.run_clustering)
        thread.daemon = True
        thread.start()

    def run_clustering(self) -> bool:
        """Runs Louvain community detection on a snapshot of the graph and updates Neo4j."""
        # Use a lock to prevent parallel clustering runs
        if not self._lock.acquire(blocking=False):
            logger.warning("Community detection is already running.")
            return False
            
        try:
            if not self.client or not self.client.verify_connection():
                logger.warning("Neo4j offline. Cannot run community detection.")
                return False
                
            logger.info("Fetching graph snapshot for Louvain clustering...")
            
            # 1. Pull graph snapshot from Neo4j
            nodes_query = "MATCH (n:Entity) RETURN n.name AS name"
            edges_query = "MATCH (s:Entity)-[r:FACT]->(t:Entity) RETURN s.name AS source, t.name AS target, r.confidence AS confidence"
            
            G = nx.Graph()
            
            with self.client.driver.session(database=self.client.database) as session:
                # Add nodes
                nodes_res = session.run(nodes_query)
                for rec in nodes_res:
                    G.add_node(rec["name"])
                    
                # Add edges
                edges_res = session.run(edges_query)
                for rec in edges_res:
                    G.add_edge(rec["source"], rec["target"], weight=rec.get("confidence", 0.5))
                    
            if len(G.nodes) == 0:
                logger.info("Graph is empty. Skipping community detection.")
                return False
                
            logger.info(f"Loaded snapshot with {len(G.nodes)} nodes and {len(G.edges)} edges. Running partition...")
            
            # 2. Run Louvain clustering
            # community_louvain.best_partition expects a networkx Graph
            partitions = community_louvain.best_partition(G, weight='weight')
            
            logger.info(f"Louvain clustering finished. Identified {len(set(partitions.values()))} communities. Writing back to DB...")
            
            # 3. Write community_id back to Neo4j
            write_query = """
            MATCH (n:Entity) WHERE n.name = $name
            SET n.community_id = $community_id
            """
            
            with self.client.driver.session(database=self.client.database) as session:
                # Use a transaction for writeback speed
                with session.begin_transaction() as tx:
                    for name, community_id in partitions.items():
                        tx.run(write_query, name=name, community_id=int(community_id))
                    tx.commit()
            
            # 4. Update metadata
            current_count = self.client.get_triple_count()
            self.update_metadata(current_count)
            logger.info(f"Community detection completed successfully. Community IDs written to Neo4j.")
            return True
            
        except Exception as e:
            logger.error(f"Error running community detection: {e}", exc_info=True)
            return False
        finally:
            self._lock.release()
