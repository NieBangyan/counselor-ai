from typing import Any


SYSTEM_PROMPT = """
你是一名高校学生政策问答助手。

你的回答必须严格依据提供的《学生手册》检索结果，不得自行编造、补充或猜测学校政策。

回答要求：
1. 优先直接回答学生的问题。
2. 如果检索资料足以回答，就给出明确结论。
3. 如果资料不足，请明确说明“根据当前检索到的《学生手册》内容，无法确认”，不要编造。
4. 不要把一般常识当作学校正式规定。
5. 尽量注明对应的制度名称、章节、条款和页码。
6. 表达简洁、清楚、适合直接面向学生使用。
""".strip()


def build_context(results: list[dict[str, Any]]) -> str:
    """
    将 Retriever 返回的结果整理成给大模型看的上下文。
    """
    blocks: list[str] = []

    for index, item in enumerate(results, start=1):
        document_title = item.get("document_title") or "未标注制度"
        chapter = item.get("chapter") or "未标注章节"
        article = item.get("article") or "未标注条款"
        pages = item.get("pdf_pages") or []
        content = item.get("content") or ""

        page_text = "、".join(str(page) for page in pages) if pages else "未标注"

        block = (
            f"【资料{index}】\n"
            f"制度：{document_title}\n"
            f"章节：{chapter}\n"
            f"条款：{article}\n"
            f"PDF页码：{page_text}\n"
            f"内容：{content}"
        )

        blocks.append(block)

    return "\n\n".join(blocks)


def build_user_prompt(
    question: str,
    results: list[dict[str, Any]],
) -> str:
    """
    构造最终发送给 DeepSeek 的用户消息。
    """
    context = build_context(results)

    return (
        f"以下是从《学生手册》中检索到的相关资料：\n\n"
        f"{context}\n\n"
        f"【学生问题】\n"
        f"{question}\n\n"
        f"请严格依据以上资料回答。"
    )