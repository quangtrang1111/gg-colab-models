import os, time
os.environ["HF_HOME"]="/content/hf"
os.environ["HF_HUB_ENABLE_HF_TRANSFER"]="1"
from huggingface_hub import list_repo_files, hf_hub_download
repo="unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF"
files=list_repo_files(repo)
c=[f for f in files if f.lower().endswith(".gguf") and "iq3_xxs" in f.lower()]
if not c:
    c=[f for f in files if f.lower().endswith(".gguf") and "iq3" in f.lower()]
assert c, "no iq3 gguf found"
fn=c[0]
print("downloading", fn, flush=True)
path=hf_hub_download(repo, fn, local_dir="/content/gguf")
print("DONE", path, f"{os.path.getsize(path)/1e9:.2f} GB", flush=True)