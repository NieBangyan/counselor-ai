import json
import re
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent

INPUT_PATH = PROJECT_ROOT / "storage" / "student_handbook.txt"
OUTPUT_PATH = PROJECT_ROOT / "storage" / "handbook_chunks.json"


# 识别 extract_pdf.py 写入的页码标记：
# ===== PDF第 18 页 =====
PAGE_PATTERN = re.compile(
    r"^=+\s*PDF第\s*(\d+)\s*页\s*=+$"
)

# 识别：
# 第一章 总则
# 第二章　入学与注册
CHAPTER_PATTERN = re.compile(
    r"^(第[一二三四五六七八九十百零〇两]+章)\s*(.*)$"
)

# 识别：
# 第一条 为了规范……
# 第十一条 学生请假……
ARTICLE_PATTERN = re.compile(
    r"^(第[一二三四五六七八九十百零〇两]+条)\s*(.*)$"
)

# 目录中的标题通常形如：
# 四、清华大学本科生学籍管理规定……………………12
TOC_TITLE_PATTERN = re.compile(
    r"^[一二三四五六七八九十百零〇两]+、(.+?)(?:…+|\s+\d+\s*$)"
)

# 正文中的制度标题通常包含这些结尾。
DOCUMENT_TITLE_ENDINGS = (
    "规定",
    "办法",
    "细则",
    "准则",
    "公约",
    "章程",
    "要求",
    "说明",
    "时间表",
    "对照表",
)


def clean_line(line: str) -> str:
    """
    清理单行文本中的多余空格和特殊空白字符。
    """
    line = line.replace("\u3000", " ")
    line = line.replace("\xa0", " ")
    line = re.sub(r"[ \t]+", " ", line)
    return line.strip()


def is_noise_line(line: str) -> bool:
    """
    判断是否是页眉、页脚或无意义的独立页码。
    """
    if not line:
        return True

    # 例如：01、12、169
    if re.fullmatch(r"\d{1,3}", line):
        return True

    # 常见页眉
    if re.fullmatch(r"2025\s*年\s*学生手册", line):
        return True

    return False


def looks_like_document_title(line: str) -> bool:
    """
    判断某一行是否可能是一个规章制度标题。

    为避免误判，要求：
    1. 字符较短；
    2. 不以“第X章”或“第X条”开头；
    3. 以常见制度名称结尾。
    """
    if not line:
        return False

    if len(line) > 45:
        return False

    if CHAPTER_PATTERN.match(line):
        return False

    if ARTICLE_PATTERN.match(line):
        return False

    # 排除修订说明和括号信息
    if line.startswith(("（", "(", "经 ", "附件")):
        return False

    return line.endswith(DOCUMENT_TITLE_ENDINGS)


def merge_content_lines(lines: list[str]) -> str:
    """
    把PDF中被换行拆开的正文重新连接起来。
    """
    cleaned: list[str] = []

    for line in lines:
        line = clean_line(line)

        if not line or is_noise_line(line):
            continue

        cleaned.append(line)

    if not cleaned:
        return ""

    # 中文规章文本通常不需要在每行之间加入空格。
    return "".join(cleaned)


def save_current_article(
    chunks: list[dict[str, Any]],
    document_title: str | None,
    chapter: str | None,
    article: str | None,
    content_lines: list[str],
    page_numbers: set[int],
) -> None:
    """
    将当前正在收集的条款保存为一个chunk。
    """
    if not article:
        return

    content = merge_content_lines(content_lines)

    if not content:
        return

    chunks.append(
        {
            "id": len(chunks) + 1,
            "document_title": document_title,
            "chapter": chapter,
            "article": article,
            "content": content,
            "pdf_pages": sorted(page_numbers),
        }
    )


def parse_handbook(text: str) -> list[dict[str, Any]]:
    """
    解析学生手册文本，按条款生成结构化数据。
    """
    chunks: list[dict[str, Any]] = []

    current_page: int | None = None
    current_document_title: str | None = None
    current_chapter: str | None = None
    current_article: str | None = None

    current_content_lines: list[str] = []
    current_article_pages: set[int] = set()

    lines = text.splitlines()

    for raw_line in lines:
        line = clean_line(raw_line)

        if not line:
            continue

        # 1. 页码标记
        page_match = PAGE_PATTERN.match(line)

        if page_match:
            current_page = int(page_match.group(1))

            # 当前条款跨页时，把新页码也记录进去。
            if current_article is not None:
                current_article_pages.add(current_page)

            continue

        if is_noise_line(line):
            continue

        # 2. 目录标题
        toc_match = TOC_TITLE_PATTERN.match(line)

        if toc_match:
            # 目录只用于识别名称，不作为正文标题使用。
            continue

        # 3. 规章制度标题
        if looks_like_document_title(line):
            save_current_article(
                chunks=chunks,
                document_title=current_document_title,
                chapter=current_chapter,
                article=current_article,
                content_lines=current_content_lines,
                page_numbers=current_article_pages,
            )

            current_document_title = line
            current_chapter = None
            current_article = None
            current_content_lines = []
            current_article_pages = set()

            continue

        # 4. 章节标题
        chapter_match = CHAPTER_PATTERN.match(line)

        if chapter_match:
            save_current_article(
                chunks=chunks,
                document_title=current_document_title,
                chapter=current_chapter,
                article=current_article,
                content_lines=current_content_lines,
                page_numbers=current_article_pages,
            )

            chapter_number = chapter_match.group(1)
            chapter_name = chapter_match.group(2).strip()

            current_chapter = (
                f"{chapter_number} {chapter_name}"
                if chapter_name
                else chapter_number
            )

            current_article = None
            current_content_lines = []
            current_article_pages = set()

            continue

        # 5. 条款标题
        article_match = ARTICLE_PATTERN.match(line)

        if article_match:
            save_current_article(
                chunks=chunks,
                document_title=current_document_title,
                chapter=current_chapter,
                article=current_article,
                content_lines=current_content_lines,
                page_numbers=current_article_pages,
            )

            current_article = article_match.group(1)
            first_content = article_match.group(2).strip()

            current_content_lines = []
            current_article_pages = set()

            if current_page is not None:
                current_article_pages.add(current_page)

            if first_content:
                current_content_lines.append(first_content)

            continue

        # 6. 普通正文
        if current_article is not None:
            current_content_lines.append(line)

            if current_page is not None:
                current_article_pages.add(current_page)

    # 保存最后一个条款
    save_current_article(
        chunks=chunks,
        document_title=current_document_title,
        chapter=current_chapter,
        article=current_article,
        content_lines=current_content_lines,
        page_numbers=current_article_pages,
    )

    return chunks


def validate_chunks(chunks: list[dict[str, Any]]) -> None:
    """
    做一些简单的数据质量检查。
    """
    missing_title = sum(
        chunk["document_title"] is None
        for chunk in chunks
    )

    missing_chapter = sum(
        chunk["chapter"] is None
        for chunk in chunks
    )

    short_content = sum(
        len(chunk["content"]) < 15
        for chunk in chunks
    )

    print(f"条款总数：{len(chunks)}")
    print(f"缺少制度标题：{missing_title}")
    print(f"缺少章节名称：{missing_chapter}")
    print(f"正文少于15个字符：{short_content}")


def print_examples(chunks: list[dict[str, Any]], count: int = 3) -> None:
    """
    打印前几条结果，方便检查。
    """
    print("\n结果预览：")

    for chunk in chunks[:count]:
        print("-" * 60)
        print(f"ID：{chunk['id']}")
        print(f"文件：{chunk['document_title']}")
        print(f"章节：{chunk['chapter']}")
        print(f"条款：{chunk['article']}")
        print(f"页码：{chunk['pdf_pages']}")
        print(f"内容：{chunk['content'][:200]}")


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"找不到输入文件：{INPUT_PATH}\n"
            "请先运行 src/extract_pdf.py。"
        )

    text = INPUT_PATH.read_text(encoding="utf-8")

    chunks = parse_handbook(text)

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_PATH.write_text(
        json.dumps(
            chunks,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    validate_chunks(chunks)
    print_examples(chunks)

    print(f"\nJSON已保存到：{OUTPUT_PATH}")


if __name__ == "__main__":
    main()