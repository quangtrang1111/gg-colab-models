"""ONE-TIME CPU compile + publish. Runs on a CPU-only Colab VM (no GPU quota).
Installs CUDA 12 toolkit (nvcc + headers + libs), compiles llama-server for sm75,
bundles the binary + ggml libs + CUDA runtime libs (portable), publishes to public HF.
Logs milestones; prints PUBLISHED at the end. Token used only for this upload.
"""
import os, subprocess, sys, time, tarfile, shutil, glob
os.environ["DEBIAN_FRONTEND"] = "noninteractive"
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
def log(*a): print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)
def sh(c, **kw): return subprocess.run(["bash","-c",c], **kw)

CUDA = "/usr/local/cuda-12.6"
if not os.path.exists(f"{CUDA}/bin/nvcc"):
    log("installing CUDA 12.6 toolkit components...")
    sh("wget -q https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb -O /tmp/cuda-keyring.deb", check=True)
    sh("dpkg -i /tmp/cuda-keyring.deb", check=True)
    sh("apt-get update -qq", check=True)
    sh("apt-get install -y -qq cuda-nvcc-12-6 cuda-cudart-dev-12-6 libcublas-dev-12-6 cuda-cccl-12-6", check=True)
log("CUDA_INSTALLED", os.path.exists(f"{CUDA}/bin/nvcc"))
os.environ["PATH"] = f"{CUDA}/bin:" + os.environ.get("PATH","")
os.environ["CUDAToolkit_ROOT"] = CUDA

if not os.path.isdir("/content/llama.cpp"):
    log("cloning llama.cpp")
    sh("git clone --depth 1 https://github.com/ggml-org/llama.cpp /content/llama.cpp", check=True)
log("cmake configure (CUDA sm75)")
sh(f'cmake -B /content/llama.cpp/build -S /content/llama.cpp -DGGML_CUDA=ON '
   f'-DCMAKE_CUDA_ARCHITECTURES=75 -DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=OFF '
   f'-DCUDAToolkit_ROOT={CUDA}', check=True)
log("cmake build llama-server (CPU compile, ~30 min)")
sh("cmake --build /content/llama.cpp/build --config Release -j2 --target llama-server", check=True)
binp = "/content/llama.cpp/build/bin/llama-server"
assert os.path.exists(binp), "binary missing"
log("BUILD_DONE", binp)

# Stage bundle: bin/ + all build .so (rel paths) + CUDA runtime libs in lib/.
STAGE = "/content/bundle"
shutil.rmtree(STAGE, ignore_errors=True)
shutil.copytree("/content/llama.cpp/build/bin", f"{STAGE}/bin")
for root,_,files in os.walk("/content/llama.cpp/build"):
    for f in files:
        if f.endswith(".so") or ".so." in f:
            full = os.path.join(root,f); rel = os.path.relpath(full,"/content/llama.cpp/build")
            if not rel.startswith("bin/"):
                dst = os.path.join(STAGE,rel); os.makedirs(os.path.dirname(dst),exist_ok=True)
                shutil.copy2(full,dst)
os.makedirs(f"{STAGE}/lib",exist_ok=True)
for pat in ["libcudart.so*","libcublas.so*","libcublasLt.so*"]:
    for src in glob.glob(f"{CUDA}/lib64/{pat}") + glob.glob(f"{CUDA}/targets/x86_64-linux/lib/{pat}"):
        if os.path.isfile(src) and not os.path.islink(src):
            shutil.copy2(src, f"{STAGE}/lib/{os.path.basename(src)}")
OUT = "/content/llama-server-cuda-sm75.tar.gz"
with tarfile.open(OUT,"w:gz") as tar:
    tar.add(STAGE, arcname=".")
log("bundle MB:", round(os.path.getsize(OUT)/1e6,1))

from huggingface_hub import HfApi
TOKEN = os.environ.get("HF_TOKEN", "")
REPO = "quangtrang/llama-server-colab-t4"
api = HfApi(token=TOKEN)
api.create_repo(REPO, repo_type="model", private=False, exist_ok=True)
api.upload_file(path_or_fileobj=OUT, path_in_repo="llama-server-cuda-sm75.tar.gz",
                repo_id=REPO, repo_type="model")
log("PUBLISHED:", f"https://huggingface.co/{REPO}")