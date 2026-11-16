import subprocess, os, re
def sh(c): return subprocess.run(["bash","-c",c],capture_output=True,text=True).stdout
def a(s): return s.encode("ascii","replace").decode()
log = open("/content/llama.log", errors="replace").read() if os.path.exists("/content/llama.log") else ""
lines = [l for l in log.splitlines() if re.search(r"prompt|token|ctx|n_ctx|slot|error|exceed", l, re.I)]
print("LOG_HITS:")
for l in lines[-25:]:
    print(" ", a(l).strip()[:190])
print("GPU:", a(sh("nvidia-smi --query-gpu=memory.used,memory.total --format=csv"))[:120])