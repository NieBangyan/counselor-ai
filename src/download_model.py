from modelscope import snapshot_download

model_dir = snapshot_download(
    model_id="BAAI/bge-small-zh-v1.5",
    cache_dir="models"
)

print(model_dir)