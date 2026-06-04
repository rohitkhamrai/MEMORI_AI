# MemoriaAI Project Memory & Changelog

This directory serves as the persistent memory storage for MemoriaAI development tasks, tracking updates, features, bug fixes, and architectural adjustments.

## [2026-06-03] Project Bootstrapping

### Added
- Created repository layout structure.
- Defined initial project roadmap and memory tracking process in `memory/changelog.md`.
- Proposed Python 3.13 project specification with Neo4j & Local Embeddings (`sentence-transformers`).
- Implemented `memoria/schema.py` containing Pydantic models for nodes, edges, payloads, and final report deliverables.
- Implemented `memoria/router.py` containing the 4-phase Cognitive Maturity Router.
- Implemented `memoria/database/neo4j_client.py` with native vector index and Topological Context Break logic to mitigate collisions.
- Implemented `memoria/cli.py` exposing the `memoria research` command.
- Set up unit tests in `tests/test_router.py` and `tests/test_schemas.py` (5 tests passing).

### Fixed
- Resolved PowerShell installer `$Args` variable conflict by using direct `npx` execution bypass.

## [2026-06-03] Fact Extraction & Embedding Pipeline

### Added
- Implemented `EmbeddingEngine` in `memoria/embeddings.py` (singleton class utilizing local `SentenceTransformer('all-MiniLM-L6-v2')` model).
- Implemented `FactExtractor` in `memoria/parser/extraction.py` supporting:
  1. API mode via `instructor` OpenAI-compatible client wrapper (automatically configures for Gemini or OpenAI).
  2. Heuristic offline fallback mode utilizing regex to extract subject-verb-object relationships.
- Integrated extraction, embedding generation, and Neo4j ingest under `memoria ingest` CLI command in `memoria/cli.py`.
- Added unit and integration tests in `tests/test_extraction.py` (all 8 tests passing).

### Memory Notes
- Python environment has two versions (3.11 and 3.13). Pytest and pip installed packages must be run using Python 3.11 context: `C:\Users\rohit\AppData\Local\Programs\Python\Python311\python.exe`.
- Tested offline fallback and CLI invocation. Runs end-to-end without active API keys or live Neo4j.

## [2026-06-03] Production-Grade Governance, Search & Query Features (v3 Plan)

### Added
- Abstracted `SearchProvider` layer in `memoria/ingestion/search_engine.py` supporting DDG, Brave, Serper, and Tavily.
- Dynamic `SourceScorer` in `memoria/memory/source_scorer.py` using domain authority, exponential recency decay, and cross-source agreement formulas.
- `EntityResolver` in `memoria/memory/entity_resolver.py` supporting lexical matching, alias tracking, embedding similarity thresholds, and topological context collision checks.
- `ClaimVersioner` in `memoria/memory/claim_versioning.py` implementing historical version tracking (`ClaimVersion` nodes with `HAS_VERSION` edges).
- `HubRegistry` in `memoria/memory/hub_registry.py` caching high-degree entity hubs to mitigate neighborhood explosions.
- `CommunityDetector` in `memoria/memory/community_detector.py` providing asynchronous Louvain community partition updates on networkx graphs, triggered periodically (every 10k triples or 5k initial).
- `ContradictionResolver` in `memoria/memory/contradiction_resolver.py` grouping claims to extract Dominant View, Minority View, and Consensus Confidence.
- `KnowledgeGapDetector` in `memoria/memory/knowledge_gap_detector.py` analyzing active subgraphs for isolated nodes, missing comparative links, and stale contexts.
- `TemporalDecayEngine` in `memoria/temporal/decay.py` calculating stability indices.
- `PriorityQueueRefreshWorker` in `memoria/temporal/refresh_worker.py` prioritizing background refreshes using centrality, query frequency, and decay scores.
- `ReportGenerator` and `ReportFormatter` in `memoria/report/` compiling and styling the 5-framework research deliverable utilizing the `rich` library.
- Unit and integration tests in `tests/test_new_governance_layers.py`.

### Changed
- Re-wired the `memoria research` CLI command in `memoria/cli.py` to trigger web search, versioned ingestion, hybrid vector-graph querying, stale scans, priority queues, and formatted terminal reports.
- Modified the `memoria ingest` CLI command to include the lexical, vector, and topological entity resolution and claim versioning.
- Implemented multi-tier cost containment in `FactExtractor` (`memoria/parser/extraction.py`) utilizing dynamic confidence scoring to escalate to OpenAI/Gemini/Groq APIs only when heuristic averages drop below 0.60.

## [2026-06-03] Final Evolved Recruiter-Grade Architecture (v4 Checklist)

### Added
- `ClaimHashCache` in `memoria/parser/cost_control.py` providing sentence-level SHA256 cache mapping to avoid redundant LLM queries.
- `KnowledgeQualityManager` in `memoria/memory/quality.py` calculating importance scores using the weighted formula (0.4 * authority + 0.3 * query_frequency + 0.2 * recency + 0.1 * centrality) and enforcing claim floor rejections (confidence < 0.20 or composite score < 0.25).
- Bridge Entity Protection in `memoria/query/graph_traversal.py` to identify cross-community bridge nodes and safeguard them from hub filters or depth cuts.
- `MetricsTracker` in `memoria/observability/tracker.py` logging queries, searches, latency averages, rejections, contradictions, and cache counts to `.memoria_metrics.json`.
- `ObservabilityDashboard` in `memoria/observability/dashboard.py` showing runtime statistics and querying Neo4j for node counts, edge counts, Louvain communities, and hubs.
- Dashboard command `memoria dashboard` in `cli.py` to trigger the rich visual terminal dashboard.
- Verification tests in `tests/test_final_checklist.py`.

### Changed
- Aligned `HybridQueryEngine` stage-based routing weights precisely with Stage 0-3 percentages.
- Integrated quality checks into `ClaimVersioner` and caching checks into `FactExtractor`.


