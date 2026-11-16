import urllib.request, time, subprocess
def sh(c): return subprocess.run(["bash","-c",c],capture_output=True,text=True).stdout
deadline = time.time() + 180
last = 0
while time.time() < deadline:
    try:
        with urllib.request.urlopen("http://localhost:8000/health", timeout=5) as r:
            if r.status == 200:
                print("READY health:", r.read().decode(), flush=True)
                print(sh("nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv"), flush=True)
                break
    except Exception:
        pass
    if not sh("pgrep -f llama-server").strip():
        print("LLAMA PROCESS DIED. log:", flush=True)
        print(open("/content/llama.log",errors="replace").read()[-2500:], flush=True)
        break
    if time.time() - last > 15:
        last = time.time()
        print(f"[{time.strftime('%H:%M:%S')}] ...{open('/content/llama.log',errors='replace').read()[-300:]}", flush=True)
    time.sleep(4)
else:
    print("TIMEOUT. log:", flush=True)
    print(open("/content/llama.log",errors="replace").read()[-2500:], flush=True)