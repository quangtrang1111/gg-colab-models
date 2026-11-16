"""Download Qwen3-Coder-30B-A3B-Instruct UD-IQ3_XXS GGUF + build llama.cpp (CUDA sm75).
IQ3 ~12.85GB fits fully in T4 15GB VRAM with 32K q8_0 KV -> no CPU offload -> max speed.
Run detached on the VM; logs to /content/build.log.
"""
import os, subprocess, sys, time
os.environ["HF_HOME"] = "/content/hf"
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
os.environ["PATH"] = "/usr/local/cuda/bin:" + os.environ.get("PATH","")
def log(*a): print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)

from huggingface_hub import list_repo_files, hf_hub_download
repo = "unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF"
files = list_repo_files(repo)
ggufs = [f for f in files if f.lower().endswith(".gguf")]
log("repo gguf count:", len(ggufs))
def pick(tag):
    c = [f for f in ggufs if tag in f.lower()]
    return c[0] if c else None
fn = pick("iq3_xxs") or pick("iq3") or pick("q3_k_m") or pick("q4_k_m")
if not fn:
    log("ERROR: no suitable quant found"); sys.exit(1)
log("downloading", fn)
path = hf_hub_download(repo, fn, local_dir="/content/gguf")
log("downloaded:", path, f"{os.path.getsize(path)/1e9:.2f} GB")

binp = "/content/llama.cpp/build/bin/llama-server"
# Fast path: fetch prebuilt llama-server bundle (public, no token) and skip compile.
try:
    log("trying prebuilt llama-server bundle...")
    bundle = hf_hub_download("quangtrang/llama-server-colab-t4",
                             "llama-server-cuda-sm75.tar.gz", local_dir="/content/prebuilt")
    cudalib = hf_hub_download("quangtrang/llama-server-colab-t4",
                              "cuda-runtime-sm75.tar.gz", local_dir="/content/prebuilt")
    os.makedirs("/content/llama.cpp/build", exist_ok=True)
    subprocess.run(["tar", "xzf", bundle, "-C", "/content/llama.cpp/build"], check=True)
    subprocess.run(["tar", "xzf", cudalib, "-C", "/content/llama.cpp/build"], check=True)
    venv = dict(os.environ)
    venv["LD_LIBRARY_PATH"] = os.pathsep.join(["/content/llama.cpp/build/bin",
                                               "/content/llama.cpp/build/lib",
                                               venv.get("LD_LIBRARY_PATH", "")])
    v = subprocess.run([binp, "--list-devices"], capture_output=True, text=True, env=venv)
    out = (v.stdout or "") + (v.stderr or "")
    if v.returncode == 0 and "CUDA" in out.upper():
        log("PREBUILT OK: CUDA device visible.")
        log("BUILD DONE:", binp, "exists=", os.path.exists(binp))
        sys.exit(0)
    log("prebuilt did not expose CUDA (rc=%s); compiling." % v.returncode)
    subprocess.run(["rm", "-rf", "/content/llama.cpp"])
except Exception as e:
    log("prebuilt unavailable (%s); compiling." % repr(e)[:100])
    subprocess.run(["rm", "-rf", "/content/llama.cpp"])

if not os.path.isdir("/content/llama.cpp"):
    log("cloning llama.cpp")
    subprocess.run(["git","clone","--depth","1","https://github.com/ggml-org/llama.cpp","/content/llama.cpp"], check=True)
log("cmake configure (CUDA sm75)")
subprocess.run(["cmake","-B","/content/llama.cpp/build","-S","/content/llama.cpp",
                "-DGGML_CUDA=ON","-DCMAKE_CUDA_ARCHITECTURES=75","-DCMAKE_BUILD_TYPE=Release",
                "-DGGML_NATIVE=OFF"], check=True)
log("cmake build llama-server")
subprocess.run(["cmake","--build","/content/llama.cpp/build","--config","Release","-j2","--target","llama-server"], check=True)
binp = "/content/llama.cpp/build/bin/llama-server"
log("BUILD DONE:", binp, "exists=", os.path.exists(binp))