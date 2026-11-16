import time, subprocess
def sh(c): return subprocess.run(["bash","-c",c],capture_output=True,text=True).stdout
deadline = time.time() + 3000
last = 0
while time.time() < deadline:
    log = open("/content/build.log",errors="replace").read()
    if "BUILD DONE" in log:
        print("BUILD COMPLETE", flush=True)
        print(log[-1500:], flush=True)
        break
    alive = sh("pgrep -f build_llama.py").strip()
    if not alive:
        print("BUILD PROCESS ENDED (check for errors). log tail:", flush=True)
        print(log[-2500:], flush=True)
        break
    if time.time() - last > 45:
        last = time.time()
        print(f"[{time.strftime('%H:%M:%S')}] ...{log[-350:]}", flush=True)
    time.sleep(10)
else:
    print("TIMEOUT. log tail:", flush=True)
    print(open("/content/build.log",errors="replace").read()[-2500:], flush=True)