import os
import json
import hashlib
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ClaimHashCache:
    """Caches sentence-level extraction results using MD5 hashes to prevent redundant LLM calls."""
    
    def __init__(self, cache_path: str = ".memoria_hash_cache.json"):
        self.cache_path = cache_path
        self.cache: Dict[str, Any] = {}
        self.load()

    def load(self):
        """Loads cached hashes from the local JSON file."""
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
                logger.info(f"Loaded {len(self.cache)} entries from claim hash cache.")
            except Exception as e:
                logger.warning(f"Failed to load claim hash cache: {e}")
                self.cache = {}

    def save(self):
        """Saves current cache to the local JSON file."""
        try:
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save claim hash cache: {e}")

    def _hash(self, text: str) -> str:
        """Helper to compute SHA256 hash of text."""
        return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()

    def get(self, sentence: str) -> Optional[Dict[str, Any]]:
        """Retrieves cached extraction results if available.
        
        Returns:
            Optional[Dict[str, Any]]: Dictionary with cached nodes and relationships, or None.
        """
        h = self._hash(sentence)
        if h in self.cache:
            logger.info("Claim hash cache hit. Bypassing extraction.")
            return self.cache[h]
        return None

    def set(self, sentence: str, payload_dict: Dict[str, Any]):
        """Caches extraction results for a sentence."""
        h = self._hash(sentence)
        self.cache[h] = payload_dict
        self.save()
