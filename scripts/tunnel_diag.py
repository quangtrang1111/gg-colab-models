import subprocess, os
def sh(c): return subprocess.run(["bash","-c",c],capture_output=True,text=True).stdout
def a(s): return s.encode("ascii","replace").decode()
print("CF_BIN:", os.path.exists("/usr/local/bin/cloudflared"))
print("CF_PROC:", a(sh("pgrep -af cloudflared | head -2")).replace(chr(10)," | "))
print("TUNNEL_LOG:", a(sh("tail -25 /content/tunnel.log")).replace(chr(10)," | ")[:600])
print("PORT8000:", a(sh("ss -ltnp 2>/dev/null | grep :8000 | head -2"))[:200])
print("HEALTH:", a(sh("curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/health")))