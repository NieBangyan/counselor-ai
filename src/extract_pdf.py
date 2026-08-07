from pathlib import Path

import pymupdf


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PDF_PATH = PROJECT_ROOT / "data" / "学生手册1.pdf"
OUTPUT_PATH = PROJECT_ROOT / "storage" / "student_handbook.txt"


def extract_pdf_text(pdf_path: Path) -> list[dict]:
    """逐页提取PDF文本，并保留页码信息。"""

    if not pdf_path.exists():
        raise FileNotFoundError(f"找不到PDF文件：{pdf_path}")

    pages: list[dict] = []

    with pymupdf.open(pdf_path) as document:
        print(f"PDF总页数：{len(document)}")

        for page_index, page in enumerate(document):
            text = page.get_text("text", sort=True).strip()

            pages.append(
                {
                    "pdf_page": page_index + 1,
                    "text": text,
                }
            )

    return pages


def save_as_text(pages: list[dict], output_path: Path) -> None:
    """将提取结果保存为文本，方便人工检查。"""

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        for page in pages:
            file.write(f"\n===== PDF第 {page['pdf_page']} 页 =====\n")
            file.write(page["text"])
            file.write("\n")


def main() -> None:
    pages = extract_pdf_text(PDF_PATH)
    save_as_text(pages, OUTPUT_PATH)

    non_empty_pages = sum(bool(page["text"]) for page in pages)

    print(f"成功读取页面：{non_empty_pages}/{len(pages)}")
    print(f"提取结果已保存到：{OUTPUT_PATH}")

    if pages:
        print("\n第1页内容预览：")
        print(pages[0]["text"][:500])


if __name__ == "__main__":
    main()