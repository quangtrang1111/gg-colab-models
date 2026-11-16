import os, subprocess, sys, time
os.environ["HF_HOME"] = "/content/hf"
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
os.environ["PATH"] = "/usr/local/cuda/bin:" + os.environ.get("PATH","")

def log(*a): print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)

from huggingface_hub import list_repo_files, hf_hub_download
repo = "Qwen/Qwen3-8B-GGUF"
files = list_repo_files(repo)
ggufs = [f for f in files if f.lower().endswith(".gguf")]
log("repo gguf files:", ggufs)
def pick(tag):
    c = [f for f in ggufs if tag in f.lower()]
    return c[0] if c else None
fn = pick("q4_k_m") or pick("q4_k_s") or pick("q4_0") or pick("q4")
if not fn:
    log("ERROR: no Q4 gguf found"); sys.exit(1)
log("downloading", fn)
path = hf_hub_download(repo, fn, local_dir="/content/gguf")
log("downloaded:", path, f"{os.path.getsize(path)/1e9:.2f} GB")

if not os.path.isdir("/content/llama.cpp"):
    log("cloning llama.cpp")
    subprocess.run(["git","clone","--depth","1","https://github.com/ggml-org/llama.cpp","/content/llama.cpp"], check=True)
log("cmake configure (CUDA sm75)")
subprocess.run(["cmake","-B","/content/llama.cpp/build","-S","/content/llama.cpp",
                "-DGGML_CUDA=ON","-DCMAKE_CUDA_ARCHITECTURES=75","-DCMAKE_BUILD_TYPE=Release",
                "-DGGML_NATIVE=OFF"], check=True)
log("cmake build llama-server (this takes several minutes on 2 CPUs)")
subprocess.run(["cmake","--build","/content/llama.cpp/build","--config","Release","-j2","--target","llama-server"], check=True)
binp = "/content/llama.cpp/build/bin/llama-server"
log("BUILD DONE:", binp, "exists=", os.path.exists(binp))