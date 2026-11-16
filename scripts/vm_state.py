"""Print VM deployment state for the restorer to poll. Run via colab exec -f."""
import os, re, urllib.request, subprocess
def sh(c): return subprocess.run(["bash","-c",c],capture_output=True,text=True).stdout
blog = open("/content/build.log",errors="replace").read() if os.path.exists("/content/build.log") else ""
print("BUILD_DONE:", "BUILD DONE" in blog)
print("BUILD_ALIVE:", bool(sh("pgrep -f 'build_llama.py|build_30b.py'").strip()))
print("BUILD_TAIL:", blog[-160:].encode("ascii","replace").decode().replace("\n"," "))
try:
    with urllib.request.urlopen("http://localhost:8000/health",timeout=5) as r:
        print("LLAMA_HEALTH:", r.status)
except Exception:
    print("LLAMA_HEALTH: ERR")
print("LLAMA_ALIVE:", bool(sh("pgrep -f llama-server").strip()))
tlog = open("/content/tunnel.log",errors="replace").read() if os.path.exists("/content/tunnel.log") else ""
m = re.findall(r"https://[a-z0-9-]+\.trycloudflare\.com", tlog)
print("TUNNEL_URL:", m[-1] if m else "")