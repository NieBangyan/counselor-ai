from pathlib import Path

from modelscope import snapshot_download


PROJECT_ROOT = Path(__file__).resolve().parent.parent

MODEL_NAME = "BAAI/bge-reranker-base"
MODEL_DIR = PROJECT_ROOT / "models" / "bge-reranker-base"


def main() -> None:
    MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(f"正在下载模型：{MODEL_NAME}")
    print(f"保存位置：{MODEL_DIR}")

    downloaded_path = snapshot_download(
        model_id=MODEL_NAME,
        local_dir=str(MODEL_DIR),
    )

    print("模型下载完成。")
    print(downloaded_path)


if __name__ == "__main__":
    main()