from pathlib import Path

import torch
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,S
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = PROJECT_ROOT / "models" / "bge-reranker-base"


def main() -> None:
    print("正在加载 tokenizer...")

    tokenizer = AutoTokenizer.from_pretrained(
        str(MODEL_PATH),
        local_files_only=True,
    )

    print("正在加载 reranker 模型...")

    model = AutoModelForSequenceClassification.from_pretrained(
        str(MODEL_PATH),
        local_files_only=True,
    )

    model.eval()

    query = "连续两个学期取得学分太少会怎么样？"

    passages = [
        (
            "第二十六条：在学校规定的最长学习年限内，"
            "学生可以申请休学分阶段完成学业。"
            "一学期因病假、事假缺课累计达该学期课程总学时"
            "三分之一的，应当休学。"
        ),
        (
            "第三十九条：学生连续两个学期取得的学分"
            "未达到学校规定要求的，按照相关规定处理。"
        ),
    ]

    pairs = [
        [query, passage]
        for passage in passages
    ]

    inputs = tokenizer(
        pairs,
        padding=True,
        truncation=True,
        max_length=512,
        return_tensors="pt",
    )

    with torch.no_grad():
        scores = model(**inputs).logits.view(-1)

    print()
    print("Reranker Scores")
    print("=" * 60)

    for index, score in enumerate(scores, start=1):
        print(f"候选 {index}: {score.item():.4f}")
        print(passages[index - 1])
        print()

    best_index = int(torch.argmax(scores))

    print("=" * 60)
    print(f"最终排名第一：候选 {best_index + 1}")


if __name__ == "__main__":
    main()