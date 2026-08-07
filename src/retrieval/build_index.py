import logging

import faiss
import numpy as np

from src.config import (
    EMBEDDINGS_PATH,
    FAISS_INDEX_PATH,
    INDEX_DIR,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


def main():
    logger.info("Loading embeddings...")

    embeddings = np.load(EMBEDDINGS_PATH).astype("float32")

    logger.info("Embedding shape: %s", embeddings.shape)

    dimension = embeddings.shape[1]

    logger.info("Creating FAISS index...")

    index = faiss.IndexFlatIP(dimension)

    faiss.normalize_L2(embeddings)

    index.add(embeddings)

    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    faiss.write_index(index, str(FAISS_INDEX_PATH))

    logger.info("Index saved to:")
    logger.info(FAISS_INDEX_PATH)

    logger.info("Total vectors: %d", index.ntotal)


if __name__ == "__main__":
    main()