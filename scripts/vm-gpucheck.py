import subprocess, urllib.request
print("=== nvidia-smi ===")
print(subprocess.run(["nvidia-smi"], capture_output=True, text=True).stdout)
import torch
print("torch cuda available:", torch.cuda.is_available())
try:
    print("HEALTH:", urllib.request.urlopen("http://localhost:8000/health", timeout=5).read().decode())
except Exception as e:
    print("server down:", e)