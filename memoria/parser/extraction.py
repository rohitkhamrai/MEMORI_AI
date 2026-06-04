import os
import re
import uuid
import logging
from typing import List, Optional, Tuple, Dict, Any
from pydantic import BaseModel, Field

from ..schema import EntityNode, RelationshipEdge, IngestPayload
from .cost_control import ClaimHashCache

logger = logging.getLogger(__name__)

# Pydantic models for structured output via Instructor
class ExtractedEntity(BaseModel):
    name: str = Field(..., description="Normalized lexical form of the entity, e.g. 'LangGraph'")
    aliases: List[str] = Field(default_factory=list, description="Alternative names, acronyms, or lexical keys")
    description: str = Field(..., description="A short, clear definition or context summary of the entity")

class ExtractedRelationship(BaseModel):
    source: str = Field(..., description="The name of the source entity")
    target: str = Field(..., description="The name of the target entity")
    predicate: str = Field(..., description="Normalized operational verb in UPPERCASE, e.g. 'USES', 'SUPPORTS'")
    claim: str = Field(..., description="Raw text segment or claim context proving this relation")
    confidence: float = Field(..., description="Computed confidence index (0.0 to 1.0) based on source clarity")

class IngestionSchema(BaseModel):
    entities: List[ExtractedEntity] = Field(..., description="List of all unique entities discovered in the text")
    relationships: List[ExtractedRelationship] = Field(..., description="List of all unique factual relationships discovered in the text")


class FactExtractor:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GROQ_API_KEY") or os.getenv("LLM_API_KEY")
        self.base_url = os.getenv("LLM_BASE_URL")
        self.model = os.getenv("LLM_MODEL")
        self.cache = ClaimHashCache()

        # Configure provider specific details
        if not self.api_key:
            logger.info("No API keys found. Ingestion parser will run in Heuristic Offline Mode.")
        else:
            if os.getenv("GROQ_API_KEY") and not os.getenv("OPENAI_API_KEY") and not os.getenv("GEMINI_API_KEY") and not self.base_url:
                self.base_url = "https://api.groq.com/openai/v1"
                self.model = self.model or "llama-3.3-70b-versatile"
            elif os.getenv("GEMINI_API_KEY") and not os.getenv("OPENAI_API_KEY") and not self.base_url:
                self.base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
                self.model = self.model or "gemini-1.5-flash"
            elif os.getenv("OPENAI_API_KEY") and not self.base_url:
                self.model = self.model or "gpt-4o-mini"
            else:
                self.model = self.model or "gpt-4o-mini"

    def extract(self, text: str) -> IngestPayload:
        """Parses the text and returns an IngestPayload with cost containment and caching."""
        if not text.strip():
            return IngestPayload()

        # Split text into sentences for cache evaluation
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
        
        cached_nodes: List[EntityNode] = []
        cached_relationships: List[RelationshipEdge] = []
        uncached_sentences: List[str] = []
        
        # Check cache
        for sentence in sentences:
            cached_data = self.cache.get(sentence)
            if cached_data:
                # Load from cache dict
                try:
                    for n in cached_data.get("nodes", []):
                        cached_nodes.append(EntityNode(**n))
                    for r in cached_data.get("relationships", []):
                        cached_relationships.append(RelationshipEdge(**r))
                except Exception as e:
                    logger.warning(f"Failed parsing cached data for sentence '{sentence[:30]}': {e}")
                    uncached_sentences.append(sentence)
            else:
                uncached_sentences.append(sentence)

        if not uncached_sentences:
            logger.info("All claims resolved via ClaimHashCache.")
            # Deduplicate nodes by name
            unique_nodes = self._deduplicate_nodes(cached_nodes)
            return IngestPayload(nodes=unique_nodes, relationships=cached_relationships)

        # Run extraction on uncached segment
        miss_text = " ".join(uncached_sentences)
        logger.info(f"Running extraction on {len(uncached_sentences)} uncached sentences.")
        
        # 1. Run Heuristic extraction first
        payload = self._extract_via_heuristics(miss_text)
        
        # Calculate average confidence
        avg_confidence = 0.0
        if payload.relationships:
            avg_confidence = sum(r.confidence for r in payload.relationships) / len(payload.relationships)
            
        # 2. Evaluate if we need to escalate to LLM extraction
        if avg_confidence < 0.60:
            if self.api_key:
                logger.info(f"Heuristic extraction confidence ({avg_confidence:.2f}) < 0.60. Escalating to API extraction.")
                try:
                    payload = self._extract_via_api(miss_text)
                except Exception as e:
                    logger.error(f"Escalated API extraction failed: {e}. Falling back to Heuristic payload.")
                    # Tag heuristic relationships as low confidence
                    for r in payload.relationships:
                        r.confidence = 0.30
                        setattr(r, 'low_confidence', True)
            else:
                logger.warning("LOW_QUALITY_EXTRACTION: Heuristic confidence < 0.60 but no API key configured.")
                for r in payload.relationships:
                    setattr(r, 'low_confidence', True)

        # Cache newly extracted facts by mapping them to their source sentence/claim
        # To make it robust, we save facts grouped by the exact sentence they belong to
        newly_extracted_by_sentence: Dict[str, Dict[str, List[Any]]] = {s: {"nodes": [], "relationships": []} for s in uncached_sentences}
        
        for rel in payload.relationships:
            # Match relationship back to the sentence containing it
            matched_sentence = None
            for s in uncached_sentences:
                if rel.claim in s or s in rel.claim or rel.source in s and rel.target in s:
                    matched_sentence = s
                    break
            
            # Default to first sentence if no direct match
            target_sentence = matched_sentence or uncached_sentences[0]
            newly_extracted_by_sentence[target_sentence]["relationships"].append(rel.model_dump())
            
            # Find and add nodes associated with this relationship
            for node in payload.nodes:
                if node.name == rel.source or node.name == rel.target:
                    # Avoid duplicate nodes in the same sentence group
                    if node.model_dump() not in newly_extracted_by_sentence[target_sentence]["nodes"]:
                        newly_extracted_by_sentence[target_sentence]["nodes"].append(node.model_dump())

        # Write groups to cache file
        for sentence, data in newly_extracted_by_sentence.items():
            if data["nodes"] or data["relationships"]:
                self.cache.set(sentence, data)

        # Merge cached and new
        all_nodes = cached_nodes + payload.nodes
        all_relationships = cached_relationships + payload.relationships
        
        unique_nodes = self._deduplicate_nodes(all_nodes)
        return IngestPayload(nodes=unique_nodes, relationships=all_relationships)

    def _deduplicate_nodes(self, nodes: List[EntityNode]) -> List[EntityNode]:
        """Helper to deduplicate a list of nodes by name."""
        seen = {}
        for n in nodes:
            if n.name not in seen:
                seen[n.name] = n
            else:
                # Merge description/aliases if needed
                existing = seen[n.name]
                if n.description and len(n.description) > len(existing.description):
                    existing.description = n.description
                for alias in n.aliases:
                    if alias not in existing.aliases:
                        existing.aliases.append(alias)
        return list(seen.values())

    def _extract_via_api(self, text: str) -> IngestPayload:
        """Uses Instructor and OpenAI-compatible API to parse text into structured triples."""
        import openai
        import instructor

        # Initialize standard OpenAI client wrapper
        raw_client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
        client = instructor.from_openai(raw_client)

        prompt = f"""
        Analyze the following text and extract all core semantic entities and the factual relationships (triples) connecting them.
        Format all relationships strictly as (Source Entity -> Predicate -> Target Entity).
        
        Text to analyze:
        ---
        {text}
        ---
        """

        response: IngestionSchema = client.chat.completions.create(
            model=self.model,
            response_model=IngestionSchema,
            messages=[
                {"role": "system", "content": "You are an expert NLP extraction engine that extracts factual knowledge graphs from technical documents."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0
        )

        nodes = []
        for ent in response.entities:
            nodes.append(EntityNode(
                name=ent.name.strip(),
                aliases=[a.strip() for a in ent.aliases],
                description=ent.description.strip()
            ))

        relationships = []
        for rel in response.relationships:
            relationships.append(RelationshipEdge(
                source=rel.source.strip(),
                target=rel.target.strip(),
                predicate=rel.predicate.strip().upper(),
                claim=rel.claim.strip(),
                confidence=rel.confidence
            ))

        return IngestPayload(nodes=nodes, relationships=relationships)

    def _extract_via_heuristics(self, text: str) -> IngestPayload:
        """
        Fallback parser that extracts triples from text using regular expressions
        and lexical pattern matching.
        """
        # Define common predicate verbs
        verbs = [
            r"uses?", r"supports?", r"coordinates?", r"implements?", r"eliminates?", 
            r"features?", r"contains?", r"manages?", r"requires?", r"is", r"are"
        ]
        verb_pattern = r"\b(" + "|".join(verbs) + r")\b"

        # Split text into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        entities_dict = {}
        relationships = []

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Look for a Match: Entity1 -> Verb -> Entity2
            # Split sentence on the first verb found
            match = re.search(verb_pattern, sentence, re.IGNORECASE)
            if match:
                verb = match.group(1)
                parts = re.split(re.escape(verb), sentence, maxsplit=1, flags=re.IGNORECASE)
                if len(parts) == 2:
                    left, right = parts[0].strip(), parts[1].strip()
                    
                    # Clean up left (source)
                    left_words = left.split()
                    if left_words:
                        source = " ".join(left_words[-3:])  # limit to last 3 words
                    else:
                        continue
                        
                    # Clean up right (target)
                    right_clean = re.split(r'[,.;]', right)[0].strip()
                    right_words = right_clean.split()
                    if right_words:
                        target = " ".join(right_words[:4])  # limit to first 4 words
                    else:
                        continue

                    # Clean labels
                    source = re.sub(r'^[^\w]+|[^\w]+$', '', source).strip()
                    target = re.sub(r'^[^\w]+|[^\w]+$', '', target).strip()
                    predicate = verb.upper()

                    # Filter out short or garbage words
                    if len(source) < 2 or len(target) < 2:
                        continue

                    # Record unique entities
                    for ent_name in [source, target]:
                        if ent_name not in entities_dict:
                            entities_dict[ent_name] = EntityNode(
                                name=ent_name,
                                aliases=[],
                                description=f"Entity extracted from context: '{sentence[:60]}...'"
                            )

                    # Dynamic confidence scoring
                    if predicate in ["IS", "ARE"]:
                        confidence = 0.50
                    else:
                        confidence = 0.70
                        
                    # Penalize complex or overly long sentences
                    if len(sentence) > 100:
                        confidence -= 0.15
                    if "but" in sentence.lower() or "however" in sentence.lower():
                        confidence -= 0.10
                        
                    confidence = round(max(0.10, min(0.95, confidence)), 4)

                    # Create relationship
                    relationships.append(RelationshipEdge(
                        source=source,
                        target=target,
                        predicate=predicate,
                        claim=sentence,
                        confidence=confidence
                    ))

        return IngestPayload(nodes=list(entities_dict.values()), relationships=relationships)
