from sentence_transformers import SentenceTransformer
from typing import List
import logging

logger = logging.getLogger(__name__)

class EmbeddingEngine:
    _instance = None
    _model = None

    def __new__(cls, model_name: str = "all-MiniLM-L6-v2"):
        """Singleton to avoid reloading the model multiple times."""
        if cls._instance is None:
            cls._instance = super(EmbeddingEngine, cls).__new__(cls)
        return cls._instance

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        if self._model is None:
            try:
                logger.info(f"Loading SentenceTransformer model '{model_name}'...")
                self._model = SentenceTransformer(model_name)
                logger.info("Model loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
                self._model = None

    def get_embedding(self, text: str) -> List[float]:
        """Generates a 384-dimensional embedding vector for a single text string."""
        if self._model is None:
            # Fallback to a zero-filled vector if model is unavailable
            return [0.0] * 384
        try:
            embeddings = self._model.encode([text])
            return [float(x) for x in embeddings[0]]
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return [0.0] * 384

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generates a list of embedding vectors for multiple text strings."""
        if not texts:
            return []
        if self._model is None:
            return [[0.0] * 384 for _ in texts]
        try:
            embeddings = self._model.encode(texts)
            return [[float(x) for x in emb] for emb in embeddings]
        except Exception as e:
            logger.error(f"Batch embedding generation failed: {e}")
            return [[0.0] * 384 for _ in texts]
