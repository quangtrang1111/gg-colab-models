"""Launch cloudflared quick tunnel to localhost:8000. Run via colab exec."""
import subprocess, os

log = open("/content/tunnel.log", "w")
p = subprocess.Popen(["cloudflared", "tunnel", "--url", "http://localhost:8000",
                      "--no-autoupdate"],
                     stdout=log, stderr=subprocess.STDOUT,
                     stdin=subprocess.DEVNULL, start_new_session=True)
print("cloudflared started, pid", p.pid)