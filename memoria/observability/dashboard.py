import logging
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich.text import Text
from rich.align import Align

from .tracker import MetricsTracker
from ..database.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)

class ObservabilityDashboard:
    """Queries database and tracker metrics and renders a beautiful console dashboard."""
    
    def __init__(self, neo4j_client: Neo4jClient):
        self.client = neo4j_client
        self.tracker = MetricsTracker()
        self.console = Console()

    def fetch_graph_stats(self) -> dict:
        """Fetches total node, edge, community, and hub metrics from Neo4j."""
        stats = {
            "status": "Offline",
            "nodes": 0,
            "relationships": 0,
            "communities": 0,
            "hubs": 0,
            "avg_confidence": 0.0
        }
        
        if not self.client or not self.client.verify_connection():
            return stats
            
        stats["status"] = "Connected"
        
        queries = {
            "nodes": "MATCH (n:Entity) RETURN count(n) AS count",
            "relationships": "MATCH ()-[r:FACT]->() RETURN count(r) AS count",
            "communities": "MATCH (n:Entity) WHERE n.community_id IS NOT NULL RETURN count(DISTINCT n.community_id) AS count",
            "hubs": "MATCH (n:Entity) WHERE n.degree > 50 RETURN count(n) AS count",
            "avg_confidence": "MATCH ()-[r:FACT]->() RETURN avg(r.confidence) AS avg_conf"
        }
        
        try:
            with self.client.driver.session(database=self.client.database) as session:
                for key, q in queries.items():
                    res = session.run(q)
                    record = res.single()
                    if record:
                        val = record[0]
                        stats[key] = round(val, 4) if isinstance(val, float) else (val or 0)
        except Exception as e:
            logger.error(f"Failed to fetch dashboard stats from database: {e}")
            
        return stats

    def render(self):
        """Prints the rich metrics dashboard in the console."""
        self.console.print()
        title = Text("MEMORIA_AI COGNITIVE METRICS DASHBOARD", style="bold magenta")
        self.console.print(Panel(Align.center(title), border_style="cyan"))
        self.console.print()
        
        # 1. Fetch data
        db_stats = self.fetch_graph_stats()
        runtime_stats = self.tracker.get_summary()

        # 2. Database Footprint Panel
        db_table = Table(title="Graph Database Footprint", border_style="green", show_header=True, expand=True)
        db_table.add_column("Metric Name", style="bold cyan")
        db_table.add_column("Value / State", style="bold white", justify="right")
        
        status_color = "green" if db_stats["status"] == "Connected" else "red"
        db_table.add_row("Database Status", f"[{status_color}]{db_stats['status']}[/{status_color}]")
        db_table.add_row("Total Entity Nodes", str(db_stats["nodes"]))
        db_table.add_row("Total Fact Relationships", str(db_stats["relationships"]))
        db_table.add_row("Identified Communities (Louvain)", str(db_stats["communities"]))
        db_table.add_row("Registered High-Degree Hubs", str(db_stats["hubs"]))
        db_table.add_row("Average Fact Confidence", f"{db_stats['avg_confidence']:.2%}")
        
        # 3. Ingestion & Retrieval Panel
        run_table = Table(title="Pipeline Ingestion & Retrieval Statistics", border_style="blue", show_header=True, expand=True)
        run_table.add_column("Performance Variable", style="bold cyan")
        run_table.add_column("Tallied Count / Averages", style="bold white", justify="right")
        
        run_table.add_row("Queries Swept", str(runtime_stats["query_count"]))
        run_table.add_row("Web Searches Executed", str(runtime_stats["search_count"]))
        
        # Cache hits vs misses
        hits = runtime_stats["memory_hits"]
        misses = runtime_stats["memory_misses"]
        total_lookups = hits + misses
        hit_ratio = hits / total_lookups if total_lookups > 0 else 0.0
        run_table.add_row("Cache Hits (ClaimHashCache)", f"{hits} ({hit_ratio:.1%})")
        run_table.add_row("Cache Misses", str(misses))
        
        # Latency
        run_table.add_row("Average Operation Latency", f"{runtime_stats['average_latency_ms']} ms")
        
        # Rejection rate
        acc_rate = runtime_stats["claim_acceptance_rate"]
        rej_rate = runtime_stats["claim_rejection_rate"]
        run_table.add_row("Claim Acceptance Rate", f"[green]{acc_rate:.2%}[/green]")
        run_table.add_row("Claim Rejection Rate (Quality Floor)", f"[red]{rej_rate:.2%}[/red]")
        
        # Contradictions / Refreshes
        run_table.add_row("Claims Contradicted", str(runtime_stats["contradiction_count"]))
        run_table.add_row("Incremental Revalidations (Refreshes)", str(runtime_stats["refresh_count"]))

        # Layout columns side-by-side
        self.console.print(Columns([db_table, run_table], expand=True))
        self.console.print()
        
        # Quality score evaluation
        score_text = Text()
        if db_stats["status"] == "Connected":
            quality_score = db_stats["avg_confidence"] * (1.0 - runtime_stats["claim_rejection_rate"])
            score_color = "green" if quality_score >= 0.7 else "yellow" if quality_score >= 0.5 else "red"
            score_text.append(f"OVERALL MEMORY QUALITY METRIC: {quality_score:.2%}", style=f"bold {score_color}")
        else:
            score_text.append("OVERALL QUALITY METRIC: N/A (Database Offline)", style="bold red")
            
        self.console.print(Panel(Align.center(score_text), border_style="magenta"))
        self.console.print()
