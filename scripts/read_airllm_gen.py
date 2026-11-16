base = "/usr/local/lib/python3.13/dist-packages/airllm/"
b = open(base + "airllm_base.py").read().splitlines()
print("===== base 879-960: pre/post hooks + generate (eviction proof) =====")
for i in range(878, min(960, len(b))):
    print(f"{i+1}: {b[i]}")
print("\n===== VM resources =====")
import subprocess
print(subprocess.run(["df","-h","/"],capture_output=True,text=True).stdout)
print(subprocess.run(["bash","-c","du -sh /content/airllm /content/hf 2>/dev/null"],capture_output=True,text=True).stdout)
print("=== installed pkgs ===")
print(subprocess.run(["bash","-c","pip list 2>/dev/null | grep -iE '^(transformers|bitsandbytes|accelerate|torch|fastapi|uvicorn|safetensors|hf-transfer|huggingface-hub) '"],capture_output=True,text=True).stdout)
print("=== GPU ===")
print(subprocess.run(["nvidia-smi","--query-gpu=name,memory.total,memory.used","--format=csv"],capture_output=True,text=True).stdout)