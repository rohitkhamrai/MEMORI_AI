import os
import sys
import time
import asyncio
from typing import Dict, List

# Add parent directory to path to import memoria
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from memoria.api.job_runner import _run_research_sync
from memoria.database.neo4j_client import Neo4jClient

QUERIES = [
    "What is the architecture of Transformer models?",
    "How does Retrieval-Augmented Generation (RAG) work?",
    "Who are the leading companies in humanoid robotics?"
]

def clear_database():
    """Wipes the Neo4j database to ensure a clean slate for the Cold Cache run."""
    print("Clearing graph database for clean benchmark...")
    client = Neo4jClient(
        os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        os.getenv("NEO4J_USER", "neo4j"),
        os.getenv("NEO4J_PASSWORD", "password")
    )
    if client.verify_connection():
        with client.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
    client.close()

def run_suite(name: str, queries: List[str]) -> List[Dict]:
    results = []
    print(f"\nRunning Suite: {name}")
    print("-" * 50)
    for q in queries:
        print(f"Query: {q}")
        start_time = time.time()
        
        # Run synchronous research task
        report = _run_research_sync(q)
        
        latency = time.time() - start_time
        expected = report.get("expected_searches", 3)
        actual = report.get("actual_searches", 3)
        coverage = report.get("memory_coverage", 0.0)
        
        print(f"  -> Latency: {latency:.2f}s | Searches: {actual}/{expected} | Memory Coverage: {coverage}%")
        
        results.append({
            "query": q,
            "latency": latency,
            "expected_searches": expected,
            "actual_searches": actual,
            "coverage": coverage
        })
    return results

def print_markdown_table(cold_results: List[Dict], warm_results: List[Dict]):
    # Compute averages
    def avg(lst, key):
        return sum(x[key] for x in lst) / len(lst) if lst else 0
        
    cold_searches = avg(cold_results, "actual_searches")
    warm_searches = avg(warm_results, "actual_searches")
    
    cold_latency = avg(cold_results, "latency")
    warm_latency = avg(warm_results, "latency")
    
    cold_coverage = avg(cold_results, "coverage")
    warm_coverage = avg(warm_results, "coverage")
    
    # Generate Markdown Table
    md = f"""
## 📊 Benchmark Results

| Metric | Without Memory (Stateless) | With Memory (MemoriaAI) | Improvement |
|--------|-----------------------------|--------------------------|-------------|
| **Searches per Query** | {cold_searches:.1f} | {warm_searches:.1f} | **-{(1 - warm_searches/max(0.1, cold_searches))*100:.0f}%** |
| **Average Latency** | {cold_latency:.1f}s | {warm_latency:.1f}s | **-{(1 - warm_latency/max(0.1, cold_latency))*100:.0f}%** |
| **Memory Coverage** | {cold_coverage:.1f}% | {warm_coverage:.1f}% | **+{(warm_coverage - cold_coverage):.1f}%** |

*Methodology: Ran {len(QUERIES)} complex research queries against an empty graph (Stateless), then ran the same topics against the populated graph (With Memory).*
"""
    print("\n" + "="*50)
    print(md)
    print("="*50)
    
    with open(os.path.join(os.path.dirname(__file__), "..", "benchmark_results.md"), "w", encoding="utf-8") as f:
        f.write(md)
    print("Saved to benchmark_results.md")

if __name__ == "__main__":
    print("Starting MemoriaAI Benchmark...")
    
    # 1. Stateless (Cold)
    clear_database()
    cold_results = run_suite("Cold Cache (Stateless)", QUERIES)
    
    # 2. Stateful (Warm)
    # We don't clear the database here!
    # To avoid returning the EXACT same report purely from a cache, we can slightly tweak the query 
    # to force it to use the graph rather than an exact string match if we had one. But HybridQueryEngine
    # retrieves semantic matches, so exact same query is fine.
    warm_queries = [
        "Explain Transformer models architecture",
        "Explain the process of RAG (Retrieval-Augmented Generation)",
        "Top companies building humanoid robots"
    ]
    warm_results = run_suite("Warm Cache (MemoriaAI)", warm_queries)
    
    # Print results
    print_markdown_table(cold_results, warm_results)
