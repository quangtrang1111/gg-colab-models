"""Upload the repo card (README.md) to the public HF repo. Token comes from the
HF_TOKEN env var (transient, never written to disk)."""
import os
from huggingface_hub import HfApi

HERE = os.path.dirname(os.path.abspath(__file__))
README = os.path.join(os.path.dirname(HERE), "HF_README.md")

token = os.environ["HF_TOKEN"]
REPO = "quangtrang/llama-server-colab-t4"
api = HfApi(token=token)
api.upload_file(path_or_fileobj=README,
                path_in_repo="README.md", repo_id=REPO, repo_type="model")
print("README uploaded to:", f"https://huggingface.co/{REPO}")
print("files:", api.list_repo_files(REPO, repo_type="model"))