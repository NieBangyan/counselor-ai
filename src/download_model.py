from pathlib import Path

from modelscope import snapshot_download


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = PROJECT_ROOT / "models" / "bge-small-zh-v1.5"

MODEL_DIR.mkdir(parents=True, exist_ok=True)

downloaded_path = snapshot_download(
    model_id="BAAI/bge-small-zh-v1.5",
    local_dir=str(MODEL_DIR),
)

print("Model downloaded to:")
print(downloaded_path)