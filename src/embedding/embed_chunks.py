import json
import logging
from pathlib import Path
from typing import Any

import numpy as np

from src.config import (
    CHUNKS_PATH,
    EMBEDDINGS_PATH,
    METADATA_PATH,
    EMBEDDINGS_DIR,
    EMBEDDING_BATCH_SIZE,
)
from src.embedding.model import get_embedding_model


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


def load_chunks(path: Path) -> list[dict[str, Any]]:
    """读取结构化知识块。"""
    if not path.exists():
        raise FileNotFoundError(
            f"找不到知识块文件：{path}\n"
            "请先运行知识块构建程序。"
        )

    with path.open("r", encoding="utf-8") as file:
        chunks = json.load(file)

    if not isinstance(chunks, list):
        raise ValueError("知识块文件格式错误，最外层应为列表。")

    if not chunks:
        raise ValueError("知识块文件为空。")

    return chunks


def build_embedding_text(chunk: dict[str, Any]) -> str:
    """
    组合标题、章节、条款和正文，作为向量化文本。

    只向量化正文可能损失标题信息，因此把结构信息一起加入。
    """
    parts = [
        str(chunk.get("document_title") or "").strip(),
        str(chunk.get("chapter") or "").strip(),
        str(chunk.get("article") or "").strip(),
        str(chunk.get("content") or "").strip(),
    ]

    return "\n".join(part for part in parts if part)


def build_metadata(
    chunks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """保存与每个向量一一对应的元数据。"""
    metadata: list[dict[str, Any]] = []

    for index, chunk in enumerate(chunks):
        metadata.append(
            {
                "vector_index": index,
                "id": chunk.get("id"),
                "document_title": chunk.get("document_title"),
                "chapter": chunk.get("chapter"),
                "article": chunk.get("article"),
                "content": chunk.get("content"),
                "pdf_pages": chunk.get("pdf_pages", []),
            }
        )

    return metadata


def save_embeddings(
    embeddings: np.ndarray,
    metadata: list[dict[str, Any]],
) -> None:
    """保存向量矩阵和元数据。"""
    EMBEDDINGS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    np.save(EMBEDDINGS_PATH, embeddings)

    METADATA_PATH.write_text(
        json.dumps(
            metadata,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def validate_embeddings(
    embeddings: np.ndarray,
    chunk_count: int,
) -> None:
    """检查生成结果是否符合预期。"""
    if embeddings.ndim != 2:
        raise ValueError(
            f"向量矩阵应当是二维，实际形状：{embeddings.shape}"
        )

    if embeddings.shape[0] != chunk_count:
        raise ValueError(
            "向量数量与知识块数量不一致："
            f"{embeddings.shape[0]} != {chunk_count}"
        )

    if not np.isfinite(embeddings).all():
        raise ValueError("向量中存在 NaN 或无穷值。")


def main() -> None:
    logger.info("正在读取知识块：%s", CHUNKS_PATH)

    chunks = load_chunks(CHUNKS_PATH)
    texts = [build_embedding_text(chunk) for chunk in chunks]

    empty_count = sum(not text.strip() for text in texts)

    if empty_count:
        raise ValueError(f"存在 {empty_count} 个空知识块，无法向量化。")

    logger.info("已加载 %d 个知识块", len(chunks))
    logger.info("正在加载向量模型")

    model = get_embedding_model()

    logger.info(
        "开始生成向量，batch size=%d",
        EMBEDDING_BATCH_SIZE,
    )

    embeddings = model.encode(
        texts,
        batch_size=EMBEDDING_BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    embeddings = embeddings.astype(np.float32)

    validate_embeddings(
        embeddings=embeddings,
        chunk_count=len(chunks),
    )

    metadata = build_metadata(chunks)

    save_embeddings(
        embeddings=embeddings,
        metadata=metadata,
    )

    logger.info("向量生成完成")
    logger.info("向量矩阵形状：%s", embeddings.shape)
    logger.info("向量数据类型：%s", embeddings.dtype)
    logger.info("向量文件：%s", EMBEDDINGS_PATH)
    logger.info("元数据文件：%s", METADATA_PATH)


if __name__ == "__main__":
    main()