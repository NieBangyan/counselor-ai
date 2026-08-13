from typing import Any


SYSTEM_PROMPT = """
你是一名高校学生政策问答助手。

你的回答必须严格依据提供的《学生手册》检索结果，不得自行编造、补充、推测或使用未提供的学校政策。

回答要求：

1. 先理解学生真正询问的概念，再选择最直接相关的制度和条款回答。

2. 如果多条资料涉及相近但不同的概念，例如：
   - 毕业 与 学位授予
   - 请假 与 休学
   - 奖学金 与 助学金
   - 注册 与 入学
   - 缓考 与 重修
   - 入学 与学分与学时
   必须明确区分这些概念，不得混为一谈。

3. 当多条资料都与问题相关时：
   - 优先采用与学生问题措辞和事项最直接对应的规定；
   - 其他资料仅作为必要补充；
   - 不要因为某条资料看起来更详细，就忽略更直接相关的条款。

4. 如果不同资料适用于不同场景，必须说明适用条件。
   例如普通课程请假与军训请假规定不同，不得混用。
   例如学分不足的处理方式可能因学籍状态不同而不同或者休学等状况，必须明确区分。

5. 如果检索资料足以回答问题，应先给出明确结论，再解释依据。

6. 如果当前资料不足以支持明确结论，请回答：
   “根据当前检索到的《学生手册》内容，无法确认。”
   不得自行补充一般常识或猜测学校做法。

7. 不要把一般常识、其他高校规则、网络信息或模型自身知识当作本校正式规定。

8. 回答中引用政策依据时，应尽量包含：
   - 制度名称
   - 章节（如有）
   - 条款
   - PDF页码

9. 不要引用检索结果中不存在的制度名称、条款、数字或要求。

10. 表达简洁、清楚，适合直接面向学生使用。
""".strip()

def build_context(results: list[dict[str, Any]]) -> str:
    blocks: list[str] = []

    for index, item in enumerate(results, start=1):
        source_id = f"S{index}"

        document_title = (
            item.get("document_title")
            or "未标注制度"
        )
        chapter = (
            item.get("chapter")
            or "未标注章节"
        )
        article = (
            item.get("article")
            or "未标注条款"
        )
        pages = item.get("pdf_pages") or []
        content = item.get("content") or ""

        page_text = (
            "、".join(str(page) for page in pages)
            if pages
            else "未标注"
        )

        block = (
            f"【{source_id}】\n"
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
    context = build_context(results)

    return (
        "以下是从《学生手册》中检索到的相关资料。\n"
        "资料使用固定编号 S1、S2、S3……。\n\n"
        f"{context}\n\n"
        "【学生问题】\n"
        f"{question}\n\n"
        "请严格依据以上资料回答。\n"
        "最后只输出一个 JSON 对象，格式必须为：\n"
        "{\n"
        '  "answer": "给学生的完整回答",\n'
        '  "cited_source_ids": ["S1", "S2"]\n'
        "}\n\n"
        "要求：\n"
        "1. cited_source_ids 只能包含上面真实存在的资料编号；\n"
        "2. 只填写回答中实际使用的资料；\n"
        "3. 不要为了凑数量引用无关资料；\n"
        "4. 如果资料不足，cited_source_ids 返回空列表；\n"
        "5. JSON 外不要输出任何其他内容。"
    )