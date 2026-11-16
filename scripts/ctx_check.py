import subprocess, os, re
def sh(c): return subprocess.run(["bash","-c",c],capture_output=True,text=True).stdout
def a(s): return s.encode("ascii","replace").decode()
log = open("/content/llama.log", errors="replace").read() if os.path.exists("/content/llama.log") else ""
for l in log.splitlines():
    if re.search(r"n_ctx_slot|n_ctx =|kv_unified|out of memory|OOM|failed to allocate|CUDA error", l, re.I):
        print("LOG:", a(l).strip()[:180])
print("GPU:", a(sh("nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader")).strip())
print("HEALTH:", a(sh("curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/health")).strip())
print("ALIVE:", bool(sh("pgrep -f llama-server").strip()))