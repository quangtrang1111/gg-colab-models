import subprocess, urllib.request
def sh(c): return subprocess.run(["bash","-c",c],capture_output=True,text=True).stdout
print("=== cloudflared procs ==="); print(sh("pgrep -af cloudflared") or "(none)")
print("=== llama-server procs ==="); print(sh("pgrep -af llama-server") or "(none)")
print("=== local llama health ===")
try:
    with urllib.request.urlopen("http://localhost:8000/health", timeout=5) as r:
        print(r.status, r.read().decode())
except Exception as e:
    print("ERR", e)
print("=== tunnel.log tail ==="); print(open("/content/tunnel.log",errors="replace").read()[-1800:])