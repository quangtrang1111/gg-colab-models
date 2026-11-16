"""Local watcher for the one-time CPU compile+publish. Keeps the PC awake
(SetThreadExecutionState) and pings the CPU VM every 60s so it won't idle-recycle
during the ~40-min compile. Exits when PUBLISHED or on hard failure.
"""
import subprocess, time, os, ctypes, sys
SCRIPTS = os.path.dirname(os.path.abspath(__file__))
ENV = dict(os.environ, PATH=os.path.expanduser("~/.local/bin")+os.pathsep+os.environ.get("PATH",""),
           PYTHONUNBUFFERED="1")
SESSION = "cpubuild"
ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)  # ES_CONTINUOUS|ES_SYSTEM_REQUIRED
def log(*a): print(f"[{time.strftime('%m-%d %H:%M:%S')}]", *a, flush=True)
def colab(args, timeout=300):
    return subprocess.run(["colab","--auth","oauth2",*args], capture_output=True, text=True,
                          env=ENV, stdin=subprocess.DEVNULL, timeout=timeout)
def execf(f, timeout=120):
    return colab(["exec","-s",SESSION,"--timeout",str(timeout),"-f",f"{SCRIPTS}/{f}"], timeout=timeout+60)
def upload(f):
    return colab(["upload","-s",SESSION,f"{SCRIPTS}/{f}",f"/content/{f}"], timeout=120)
def state():
    try:
        r = execf("cpu_state.py", timeout=60); d = {"_ok": True}
        for line in r.stdout.splitlines():
            if ":" in line: k,_,v = line.partition(":"); d[k.strip()] = v.strip()
        return d
    except Exception as e:
        return {"_ok": False, "_err": repr(e)}

log("CPU watcher started (PC keep-awake ON).")
if SESSION not in colab(["sessions"], timeout=90).stdout:
    r = colab(["new","-s",SESSION], timeout=300)
    log("provision CPU:", "READY" in r.stdout)
for f in ["cpu_compile_publish.py","start_cpu_build.py","cpu_state.py"]:
    upload(f)
log("scripts uploaded.")
d = state()
if d.get("PUBLISHED") == "True":
    log("already PUBLISHED."); sys.exit(0)
if d.get("BUILD_ALIVE") != "True":
    execf("start_cpu_build.py", timeout=90); log("cpu build started.")
miss = 0
while True:
    d = state()
    if not d.get("_ok"):
        miss += 1; log(f"state check failed ({d.get('_err','')[:70]}); retry {miss}.")
        if miss > 15: log("VM unreachable too long."); sys.exit(1)
        time.sleep(60); continue
    miss = 0
    if d.get("PUBLISHED") == "True":
        log("PUBLISHED OK."); break
    if d.get("BUILD_ALIVE") != "True":
        log("BUILD DIED:", d.get("BUILD_TAIL","")); sys.exit(1)
    log("building...", d.get("BUILD_TAIL","")[-90:])
    time.sleep(60)
log("CPU compile+publish complete.")