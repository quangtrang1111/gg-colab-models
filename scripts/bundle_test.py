"""Validate the published bundles are self-contained: download both anonymously,
extract, and check the binary loads with the bundled CUDA runtime libs.
"""
import os, subprocess, sys, shutil, tarfile
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
from huggingface_hub import hf_hub_download
def log(*a): print(*a, flush=True)
REPO = "quangtrang/llama-server-colab-t4"

shutil.rmtree("/content/llama.cpp", ignore_errors=True)
os.makedirs("/content/llama.cpp/build", exist_ok=True)
for fn in ["llama-server-cuda-sm75.tar.gz", "cuda-runtime-sm75.tar.gz"]:
    p = hf_hub_download(REPO, fn, local_dir="/content/prebuilt")
    log("downloaded", fn, round(os.path.getsize(p)/1e6,1), "MB")
    subprocess.run(["tar","xzf",p,"-C","/content/llama.cpp/build"], check=True)
log("extracted both bundles.")
binp = "/content/llama.cpp/build/bin/llama-server"
ld = os.pathsep.join(["/content/llama.cpp/build/bin","/content/llama.cpp/build/lib"])
env = dict(os.environ, LD_LIBRARY_PATH=ld)
r = subprocess.run([binp,"--version"], capture_output=True, text=True, env=env)
log("version rc:", r.returncode)
log("version out:", (r.stdout or r.stderr).strip()[:200])
r2 = subprocess.run(["bash","-c","ldd /content/llama.cpp/build/bin/llama-server | grep -Ei 'not found' || echo 'no missing libs'"],
                    capture_output=True, text=True, env=env)
log("ldd missing:", r2.stdout.strip()[:400])
print("BUNDLE_TEST_DONE", flush=True)