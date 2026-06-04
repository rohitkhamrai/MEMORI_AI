import os
import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class MetricsTracker:
    """Tracks runtime counters and latencies, persisting them to a local JSON file."""
    
    def __init__(self, filepath: str = ".memoria_metrics.json"):
        self.filepath = filepath
        self.metrics: Dict[str, Any] = {
            "query_count": 0,
            "search_count": 0,
            "memory_hits": 0,
            "memory_misses": 0,
            "latencies_ms": [],
            "claims_accepted": 0,
            "claims_rejected": 0,
            "contradiction_count": 0,
            "refresh_count": 0,
            "knowledge_reused": 0,
            "knowledge_new": 0,
            "expected_searches": 0,
            "actual_searches": 0,
            "history": []
        }
        self.load()

    def load(self):
        """Loads metrics from local file."""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Merge default keys in case of schema update
                    for k, v in data.items():
                        self.metrics[k] = v
            except Exception as e:
                logger.warning(f"Failed to load metrics: {e}")

    def save(self):
        """Saves metrics to local file."""
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.metrics, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")

    def increment(self, key: str, value: int = 1):
        """Increments a counter metric."""
        if key in self.metrics:
            if isinstance(self.metrics[key], int):
                self.metrics[key] += value
                self.save()

    def record_query(self): self.increment("query_count")
    def record_search(self): self.increment("search_count")
    def record_memory_hit(self): self.increment("memory_hits")
    def record_memory_miss(self): self.increment("memory_misses")
    
    def record_latency(self, latency_ms: float):
        """Records query or ingestion execution latency."""
        self.metrics["latencies_ms"].append(round(latency_ms, 2))
        # Keep last 100 entries only to save space
        if len(self.metrics["latencies_ms"]) > 100:
            self.metrics["latencies_ms"] = self.metrics["latencies_ms"][-100:]
        self.save()

    def record_claim_status(self, accepted: bool):
        """Records whether an ingested claim was accepted or rejected by quality filter."""
        key = "claims_accepted" if accepted else "claims_rejected"
        self.increment(key)

    def record_contradiction(self): self.increment("contradiction_count")
    def record_refresh(self): self.increment("refresh_count")

    def record_knowledge_usage(self, reused: int, new: int):
        """Records knowledge facts reused vs newly discovered."""
        if reused > 0:
            self.increment("knowledge_reused", reused)
        if new > 0:
            self.increment("knowledge_new", new)

    def record_search_avoidance(self, expected: int, actual: int):
        """Records when memory successfully bypassed expected web searches."""
        if expected > 0:
            self.increment("expected_searches", expected)
        if actual > 0:
            self.increment("actual_searches", actual)
        elif actual == 0 and expected > 0:
            # We avoided all searches, still want to make sure it's logged
            self.save()

    def take_snapshot(self, graph_stats: Dict[str, Any], reuse_rate: float):
        """Records a snapshot of the current state of the system."""
        import datetime
        snapshot = {
            "month": datetime.datetime.now().strftime("%b"),
            "entities": graph_stats.get("node_count", 0),
            "claims": graph_stats.get("relationship_count", 0),
            "communities": graph_stats.get("community_count", 0),
            "reuse_rate": reuse_rate
        }
        history = self.metrics.get("history", [])
        
        # Keep only one snapshot per month for the chart
        if history and history[-1].get("month") == snapshot["month"]:
            history[-1] = snapshot
        else:
            history.append(snapshot)
            
        self.metrics["history"] = history
        self.save()

    def get_summary(self) -> Dict[str, Any]:
        """Calculates averages and returns metrics summary."""
        lats = self.metrics.get("latencies_ms", [])
        avg_latency = sum(lats) / len(lats) if lats else 0.0
        
        accepted = self.metrics.get("claims_accepted", 0)
        rejected = self.metrics.get("claims_rejected", 0)
        total_claims = accepted + rejected
        acceptance_rate = accepted / total_claims if total_claims > 0 else 1.0
        rejection_rate = rejected / total_claims if total_claims > 0 else 0.0
        
        return {
            "query_count": self.metrics.get("query_count", 0),
            "search_count": self.metrics.get("search_count", 0),
            "memory_hits": self.metrics.get("memory_hits", 0),
            "memory_misses": self.metrics.get("memory_misses", 0),
            "average_latency_ms": round(avg_latency, 2),
            "claim_acceptance_rate": round(acceptance_rate, 4),
            "claim_rejection_rate": round(rejection_rate, 4),
            "contradiction_count": self.metrics.get("contradiction_count", 0),
            "refresh_count": self.metrics.get("refresh_count", 0)
        }
