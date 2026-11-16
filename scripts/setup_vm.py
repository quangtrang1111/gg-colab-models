"""Colab VM setup: check hardware, add swap, install AirLLM stack + cloudflared.
Run via: colab exec -s qwen -f setup_vm.py
"""
import subprocess, sys, shutil, os

def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    return (r.stdout + r.stderr).strip()

print("=== GPU ===")
print(run(["nvidia-smi", "--query-gpu=name,memory.total,compute_cap", "--format=csv"]))
print("=== DISK ===")
print(run(["df", "-h", "/", "/content"]))
print("=== RAM ===")
print(run(["free", "-h"]))

import torch
print("torch", torch.__version__, "| cuda", torch.version.cuda, "| available", torch.cuda.is_available())

print("=== SWAP ===")
sw = run(["swapon", "--show"])
if not sw:
    try:
        run(["fallocate", "-l", "8G", "/swapfile"], check=True)
        os.chmod("/swapfile", 0o600)
        run(["mkswap", "/swapfile"], check=True)
        run(["swapon", "/swapfile"], check=True)
        print("8G swap enabled")
    except Exception as e:
        print("swap not available (non-fatal):", e)
else:
    print(sw)

print("=== PIP INSTALL ===")
pkgs = ["airllm", "transformers>=4.57,<5", "bitsandbytes", "accelerate",
        "safetensors", "fastapi", "uvicorn", "huggingface_hub", "hf_transfer"]
r = subprocess.run([sys.executable, "-m", "pip", "install", "-q", *pkgs],
                   capture_output=True, text=True)
print(r.stdout[-3000:])
print(r.stderr[-3000:])
if r.returncode != 0:
    sys.exit("pip install failed")

import transformers, bitsandbytes
print("transformers", transformers.__version__, "| bitsandbytes", bitsandbytes.__version__)
from transformers.models.qwen3_next import modeling_qwen3_next
print("qwen3_next in-tree: OK")

print("=== CLOUDFLARED ===")
if not shutil.which("cloudflared"):
    run(["curl", "-sL", "-o", "/usr/local/bin/cloudflared",
         "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"], check=True)
    os.chmod("/usr/local/bin/cloudflared", 0o755)
print(run(["cloudflared", "--version"]))
print("SETUP DONE")