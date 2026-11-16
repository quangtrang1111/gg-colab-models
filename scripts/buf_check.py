import subprocess, os, re
def sh(c): return subprocess.run(["bash","-c",c],capture_output=True,text=True).stdout
def a(s): return s.encode("ascii","replace").decode()
log = open("/content/llama.log", errors="replace").read() if os.path.exists("/content/llama.log") else ""
pat = re.compile(r"n_ctx|KV self|model buffer size|compute buffer|KV cache|CUDA0|kv_|size =", re.I)
hits = [l for l in log.splitlines() if pat.search(l)]
seen = set(); out = []
for l in hits:
    t = a(l).strip()[:170]
    if t not in seen:
        seen.add(t); out.append(t)
print("BUFFERS:")
for l in out[:30]: print(" ", l)
print("SIZES:", a(sh("ls -la /content/gguf/ | head -5"))[:300])