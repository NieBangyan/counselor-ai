from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
STORAGE_DIR = PROJECT_ROOT / "storage"

RAW_DIR = STORAGE_DIR / "raw"
PROCESSED_DIR = STORAGE_DIR / "processed"
EMBEDDINGS_DIR = STORAGE_DIR / "embeddings"
INDEX_DIR = STORAGE_DIR / "index"

CHUNKS_PATH = PROCESSED_DIR / "handbook_chunks.json"
EMBEDDINGS_PATH = EMBEDDINGS_DIR / "handbook_embeddings.npy"
METADATA_PATH = EMBEDDINGS_DIR / "handbook_metadata.json"
FAISS_INDEX_PATH = INDEX_DIR / "handbook.index"

EMBEDDING_MODEL_NAME = str(
    PROJECT_ROOT
    / "models"
    / "bge-small-zh-v1.5"
)

EMBEDDING_BATCH_SIZE = 64
TOP_K = 5
MIN_RETRIEVAL_SCORE = 0.5