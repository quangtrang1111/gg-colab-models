"""Lean setup for llama.cpp deployment on a fresh Colab T4. Run via colab exec -f."""
import subprocess, sys, shutil, os
def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    return (r.stdout + r.stderr).strip()
print("=== GPU ==="); print(run(["nvidia-smi","--query-gpu=name,memory.total,compute_cap","--format=csv"]))
print("=== DISK ==="); print(run(["df","-h","/"]))
print("=== build tools ==="); print("cmake:", shutil.which("cmake"), "nvcc:", shutil.which("nvcc"), "gcc:", shutil.which("gcc"))
print("=== PIP ===")
r = subprocess.run([sys.executable,"-m","pip","install","-q","huggingface_hub","hf_transfer"], capture_output=True, text=True)
print(r.stdout[-1500:]); print(r.stderr[-1500:])
print("=== CLOUDFLARED ===")
if not shutil.which("cloudflared"):
    run(["curl","-sL","-o","/usr/local/bin/cloudflared",
         "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"], check=True)
    os.chmod("/usr/local/bin/cloudflared", 0o755)
print(run(["cloudflared","--version"]))
print("SETUP DONE")