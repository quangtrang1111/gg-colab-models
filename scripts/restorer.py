"""Autonomous Colab restorer (runs in WSL).
Retries T4 provisioning until free compute units replenish, then redeploys
Qwen3-8B via llama.cpp, restarts the tunnel, updates Command Code, and keeps
the VM alive with a non-expiring ping loop.
"""
import subprocess, time, os, re, sys, json

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
PROVIDERS = (os.environ.get("COMMAND_CODE_PROVIDERS")
             or os.path.expanduser("~/.commandcode/providers.json"))
ENV = dict(os.environ,
           PATH=os.path.expanduser("~/.local/bin") + ":" + os.environ.get("PATH",""),
           LD_LIBRARY_PATH=os.path.expanduser("~/.nix-profile/lib") + ":" + os.environ.get("LD_LIBRARY_PATH",""),
           PYTHONUNBUFFERED="1")
SESSION = "qwen"

def log(*a):
    print(f"[{time.strftime('%m-%d %H:%M:%S')}]", *a, flush=True)

def colab(args, timeout=300):
    return subprocess.run(["colab","--auth","oauth2",*args],
                          capture_output=True, text=True, env=ENV,
                          stdin=subprocess.DEVNULL, timeout=timeout)

def execf(fname, timeout=120):
    return colab(["exec","-s",SESSION,"--timeout",str(timeout),"-f",f"{SCRIPTS}/{fname}"], timeout=timeout+60)

def upload(fname):
    return colab(["upload","-s",SESSION,f"{SCRIPTS}/{fname}",f"/content/{fname}"], timeout=120)

def state():
    r = execf("vm_state.py", timeout=60)
    d = {}
    for line in r.stdout.splitlines():
        if ":" in line:
            k,_,v = line.partition(":")
            d[k.strip()] = v.strip()
    return d, r.stdout

# ---- Phase 1: provision retry ----
log("RESTORER started. Retrying T4 provisioning every 30 min until units replenish.")
attempt = 0
while True:
    attempt += 1
    try:
        r = colab(["new","-s",SESSION,"--gpu","T4"], timeout=300)
        if r.returncode == 0 and "READY" in r.stdout:
            log(f"T4 PROVISIONED on attempt {attempt}.")
            break
        msg = (r.stderr or r.stdout)[-180:].replace("\n"," ")
        log(f"attempt {attempt}: not available ({msg}). retry in 30 min.")
    except subprocess.TimeoutExpired:
        log(f"attempt {attempt}: provision timed out. retry in 30 min.")
    time.sleep(1800)

# ---- Phase 2: setup ----
try:
    for f in ["setup_llama_vm.py","build_llama.py","start_build.py","start_llama.py","start_tunnel.py","vm_state.py","ping.py"]:
        upload(f)
    log("scripts uploaded. running setup (deps + cloudflared)...")
    r = execf("setup_llama_vm.py", timeout=600)
    if "SETUP DONE" not in r.stdout:
        log("SETUP FAILED:", r.stdout[-800:], r.stderr[-400:]); sys.exit(1)
    log("setup done.")

    # ---- Phase 3: build + download ----
    execf("start_build.py", timeout=90)
    log("build + GGUF download started (detached). polling...")
    while True:
        d,_ = state()
        if d.get("BUILD_DONE") == "True":
            log("BUILD COMPLETE."); break
        if d.get("BUILD_ALIVE") != "True":
            log("BUILD PROCESS DIED:", d.get("BUILD_TAIL","")); sys.exit(1)
        log("building...", d.get("BUILD_TAIL","")[-90:])
        time.sleep(60)

    # ---- Phase 4: llama-server ----
    execf("start_llama.py", timeout=90)
    log("llama-server starting...")
    for _ in range(40):
        d,_ = state()
        if d.get("LLAMA_HEALTH") == "200":
            log("LLAMA SERVER READY."); break
        if d.get("LLAMA_ALIVE") != "True":
            log("LLAMA PROCESS DIED."); sys.exit(1)
        time.sleep(8)
    else:
        log("llama-server readiness timeout."); sys.exit(1)

    # ---- Phase 5: tunnel ----
    execf("start_tunnel.py", timeout=90)
    log("tunnel starting...")
    url = ""
    for _ in range(30):
        d,_ = state()
        url = d.get("TUNNEL_URL","")
        if url:
            log("TUNNEL URL:", url); break
        time.sleep(5)
    if not url:
        log("no tunnel URL obtained."); sys.exit(1)

    # ---- Phase 6: update Command Code ----
    txt = open(PROVIDERS, encoding="utf-8").read()
    new = re.sub(r"https://[a-z0-9-]+\.trycloudflare\.com", url, txt)
    open(PROVIDERS,"w",encoding="utf-8").write(new)
    log("Command Code baseURL updated to", url)
    log("RESTORE COMPLETE. Translation service live. Entering keep-alive loop.")
except SystemExit:
    raise
except Exception as e:
    log("RESTORE ERROR:", repr(e)); sys.exit(1)

# ---- Phase 7: keep-alive forever ----
while True:
    time.sleep(900)
    try:
        execf("ping.py", timeout=60)
    except Exception as e:
        log("keepalive ping error:", repr(e))