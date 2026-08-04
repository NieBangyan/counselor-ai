from functools import lru_cache
import logging

from sentence_transformers import SentenceTransformer

from src.config import EMBEDDING_MODEL_NAME


logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """Load and cache the local embedding model."""
    logger.info(
        "正在加载本地向量模型: %s",
        EMBEDDING_MODEL_NAME,
    )

    return SentenceTransformer(
        EMBEDDING_MODEL_NAME,
        device="cpu",
        local_files_only=True,
    )