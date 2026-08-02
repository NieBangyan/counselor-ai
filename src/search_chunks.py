import json
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHUNKS_PATH = PROJECT_ROOT / "storage" / "handbook_chunks.json"


def load_chunks(path: Path) -> list[dict[str, Any]]:
    """读取结构化知识库文件。"""
    if not path.exists():
        raise FileNotFoundError(
            f"找不到知识库文件：{path}\n"
            "请先运行 src/build_chunks.py。"
        )

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("知识库文件格式错误：最外层应当是列表。")

    return data


def search_chunks(
    chunks: list[dict[str, Any]],
    keyword: str,
) -> list[dict[str, Any]]:
    """
    根据关键词搜索标题、章节、条款和正文。

    当前只是调试工具，不是语义检索。
    """
    keyword = keyword.strip().lower()

    if not keyword:
        return []

    results: list[dict[str, Any]] = []

    for chunk in chunks:
        searchable_text = " ".join(
            [
                str(chunk.get("document_title") or ""),
                str(chunk.get("chapter") or ""),
                str(chunk.get("article") or ""),
                str(chunk.get("content") or ""),
            ]
        ).lower()

        if keyword in searchable_text:
            results.append(chunk)

    return results


def print_chunk(chunk: dict[str, Any]) -> None:
    """格式化输出一个知识块。"""
    print("=" * 70)
    print(f"ID：{chunk.get('id')}")
    print(f"文件：{chunk.get('document_title')}")
    print(f"章节：{chunk.get('chapter')}")
    print(f"条款：{chunk.get('article')}")
    print(f"PDF页码：{chunk.get('pdf_pages')}")
    print("-" * 70)
    print(chunk.get("content", ""))
    print()


def print_statistics(chunks: list[dict[str, Any]]) -> None:
    """输出知识库的基础统计信息。"""
    if not chunks:
        print("知识库为空。")
        return

    lengths = [
        len(str(chunk.get("content") or ""))
        for chunk in chunks
    ]

    document_counter = Counter(
        chunk.get("document_title") or "未识别标题"
        for chunk in chunks
    )

    longest_chunk = max(
        chunks,
        key=lambda item: len(str(item.get("content") or "")),
    )

    shortest_chunk = min(
        chunks,
        key=lambda item: len(str(item.get("content") or "")),
    )

    print("\n知识库统计")
    print("=" * 70)
    print(f"Chunk总数：{len(chunks)}")
    print(f"制度文件数：{len(document_counter)}")
    print(f"平均正文长度：{sum(lengths) / len(lengths):.1f} 字符")
    print(f"最长正文长度：{max(lengths)} 字符")
    print(f"最短正文长度：{min(lengths)} 字符")

    print("\n最长Chunk：")
    print(
        f"{longest_chunk.get('document_title')} / "
        f"{longest_chunk.get('article')}"
    )

    print("\n最短Chunk：")
    print(
        f"{shortest_chunk.get('document_title')} / "
        f"{shortest_chunk.get('article')}"
    )

    print("\n各制度条款数量：")
    for document_title, count in document_counter.most_common():
        print(f"{count:>4}  {document_title}")

    print("=" * 70)


def interactive_search(chunks: list[dict[str, Any]]) -> None:
    """在终端中循环搜索关键词。"""
    print("\n请输入关键词进行搜索。")
    print("例如：请假、奖学金、宿舍、重修")
    print("输入 stats 查看统计信息。")
    print("输入 exit 退出程序。\n")

    while True:
        keyword = input("搜索关键词：").strip()

        if keyword.lower() in {"exit", "quit", "q"}:
            print("程序已退出。")
            break

        if keyword.lower() == "stats":
            print_statistics(chunks)
            continue

        results = search_chunks(chunks, keyword)

        if not results:
            print(f"\n没有找到包含“{keyword}”的条款。\n")
            continue

        print(f"\n共找到 {len(results)} 条结果。\n")

        # 避免一次输出太多，只展示前10条
        for chunk in results[:10]:
            print_chunk(chunk)

        if len(results) > 10:
            print(f"还有 {len(results) - 10} 条结果未显示。\n")


def main() -> None:
    chunks = load_chunks(CHUNKS_PATH)

    print(f"已加载 {len(chunks)} 个知识块。")

    print_statistics(chunks)
    interactive_search(chunks)


if __name__ == "__main__":
    main()