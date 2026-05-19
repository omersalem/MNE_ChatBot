import logging
import numpy as np
from sentence_transformers import SentenceTransformer
from config import Config

logger = logging.getLogger(__name__)


class EmbeddingEngine:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        logger.info(f"Loading embedding model: {Config.EMBEDDING_MODEL}")
        self.model = SentenceTransformer(Config.EMBEDDING_MODEL)
        self._dimension = self.model.get_embedding_dimension()
        logger.info(f"Embedding model loaded. Dimension: {self._dimension}")
        self._initialized = True

    def embed(self, texts):
        if isinstance(texts, str):
            texts = [texts]
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.astype(np.float32)

    def embed_query(self, query):
        return self.embed(query)[0]

    @property
    def dimension(self):
        return self._dimension
