import urllib.request, time, subprocess, os

def sh(c): return subprocess.run(["bash","-c",c],capture_output=True,text=True).stdout

deadline = time.time() + 720
last = 0
while time.time() < deadline:
    try:
        with urllib.request.urlopen("http://localhost:8000/health", timeout=5) as r:
            if r.status == 200:
                print("READY:", r.read().decode(), flush=True)
                print(sh("nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv"), flush=True)
                break
    except Exception:
        pass
    alive = sh("pgrep -f run_server_vram").strip()
    if not alive:
        print("SERVER PROCESS DIED. log tail:", flush=True)
        print(open("/content/server.log",errors="replace").read()[-2500:], flush=True)
        break
    if time.time() - last > 30:
        last = time.time()
        log = open("/content/server.log",errors="replace").read()
        print(f"[{time.strftime('%H:%M:%S')}] log tail: ...{log[-400:]}", flush=True)
        print("   disk:", sh("df -h / | tail -1").strip(), "| hf:", sh("du -sh /content/hf 2>/dev/null").strip(), flush=True)
    time.sleep(5)
else:
    print("TIMEOUT waiting for readiness. log tail:", flush=True)
    print(open("/content/server.log",errors="replace").read()[-2500:], flush=True)