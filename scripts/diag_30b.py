import subprocess, os
def sh(c): return subprocess.run(["bash","-c",c],capture_output=True,text=True).stdout
print("=== llama.log tail ===")
print(open("/content/llama.log",errors="replace").read()[-3000:] if os.path.exists("/content/llama.log") else "(no log)")
print("=== llama-server proc ===")
print(sh("pgrep -af llama-server") or "(none)")
print("=== GPU ===")
print(sh("nvidia-smi --query-gpu=memory.used,memory.total --format=csv"))
print(sh("nvidia-smi --query-compute-apps=pid,used_memory --format=csv"))
print("=== port 8000 ===")
print(sh("ss -ltnp 2>/dev/null | grep :8000") or "(none)")
print("=== gguf files ===")
print(sh("find /content/gguf -name '*.gguf' -exec ls -la {} \\; 2>/dev/null"))