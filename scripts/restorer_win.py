"""Autonomous Colab restorer — WINDOWS native, resilient + resumable.
Retries T4 provisioning until free units replenish, then deploys Qwen3-Coder-30B
(Q3_K_M max-speed llama.cpp), restarts tunnel, updates Command Code, keep-alive.
Tolerates transient colab-exec timeouts; resumes an already-running build.
"""
import subprocess, time, os, re, sys, ctypes
ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)  # keep PC awake

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
PROVIDERS = (os.environ.get("COMMAND_CODE_PROVIDERS")
             or os.path.expanduser("~/.commandcode/providers.json"))
ENV = dict(os.environ,
           PATH=os.path.expanduser("~/.local/bin") + os.pathsep + os.environ.get("PATH",""),
           PYTHONUNBUFFERED="1")
SESSION = "qwen"

def log(*a): print(f"[{time.strftime('%m-%d %H:%M:%S')}]", *a, flush=True)

def colab(args, timeout=300):
    return subprocess.run(["colab","--auth","oauth2",*args],
                          capture_output=True, text=True, env=ENV,
                          stdin=subprocess.DEVNULL, timeout=timeout)

def execf(fname, timeout=120):
    return colab(["exec","-s",SESSION,"--timeout",str(timeout),"-f",f"{SCRIPTS}/{fname}"], timeout=timeout+60)

def upload(fname):
    return colab(["upload","-s",SESSION,f"{SCRIPTS}/{fname}",f"/content/{fname}"], timeout=120)

def state():
    try:
        r = execf("vm_state.py", timeout=60)
        d = {"_ok": True}
        for line in r.stdout.splitlines():
            if ":" in line:
                k,_,v = line.partition(":"); d[k.strip()] = v.strip()
        return d
    except Exception as e:
        return {"_ok": False, "_err": repr(e)}

def session_exists():
    try:
        return SESSION in colab(["sessions"], timeout=90).stdout
    except Exception:
        return False

def ensure_provisioned():
    if session_exists():
        log("session already exists; skipping provision."); return
    attempt = 0
    while True:
        attempt += 1
        try:
            r = colab(["new","-s",SESSION,"--gpu","T4"], timeout=300)
            if r.returncode == 0 and "READY" in r.stdout:
                log(f"T4 PROVISIONED on attempt {attempt}."); return
            log(f"attempt {attempt}: not available ({(r.stderr or r.stdout)[-140:].replace(chr(10),' ')}). retry 30 min.")
        except subprocess.TimeoutExpired:
            log(f"attempt {attempt}: provision timeout. retry 30 min.")
        time.sleep(1800)

def wait_build():
    d = state()
    if d.get("BUILD_DONE") == "True":
        log("build already complete."); return
    if d.get("BUILD_ALIVE") == "True":
        log("build already running; resuming watch.")
    else:
        execf("start_build_30b.py", timeout=90); log("30B build started.")
    miss = 0
    while True:
        d = state()
        if not d.get("_ok"):
            miss += 1
            log(f"state check failed ({d.get('_err','')[:70]}); retry {miss}.")
            if miss > 15: log("VM unreachable too long."); sys.exit(1)
            time.sleep(60); continue
        miss = 0
        if d.get("BUILD_DONE") == "True":
            log("BUILD COMPLETE."); return
        if d.get("BUILD_ALIVE") != "True":
            log("BUILD PROCESS DIED:", d.get("BUILD_TAIL","")); sys.exit(1)
        log("building...", d.get("BUILD_TAIL","")[-80:])
        time.sleep(60)

def wait_llama():
    execf("start_30b.py", timeout=90); log("llama-server (30B) starting...")
    for _ in range(60):
        d = state()
        if d.get("_ok"):
            if d.get("LLAMA_HEALTH") == "200":
                log("LLAMA SERVER READY."); return
            if d.get("LLAMA_ALIVE") != "True":
                log("LLAMA PROCESS DIED."); sys.exit(1)
        time.sleep(8)
    log("llama readiness timeout."); sys.exit(1)

def wait_tunnel():
    execf("start_tunnel.py", timeout=90); log("tunnel starting...")
    for _ in range(40):
        d = state()
        if d.get("_ok") and d.get("TUNNEL_URL"):
            log("TUNNEL URL:", d["TUNNEL_URL"]); return d["TUNNEL_URL"]
        time.sleep(5)
    log("no tunnel URL."); sys.exit(1)

def redeploy():
    for f in ["setup_llama_vm.py","build_30b.py","start_build_30b.py","start_30b.py","start_tunnel.py","vm_state.py","ping.py"]:
        upload(f)
    log("scripts uploaded. setup...")
    r = execf("setup_llama_vm.py", timeout=600)
    if "SETUP DONE" not in r.stdout:
        log("SETUP FAILED:", r.stdout[-600:]); sys.exit(1)
    log("setup done.")
    wait_build()
    wait_llama()
    url = wait_tunnel()
    txt = open(PROVIDERS, encoding="utf-8").read()
    open(PROVIDERS,"w",encoding="utf-8").write(re.sub(r"https://[a-z0-9-]+\.trycloudflare\.com", url, txt))
    log("Command Code baseURL updated to", url)
    log("RESTORE COMPLETE. Qwen3-Coder-30B live.")

def main():
    log("WINDOWS RESTORER (resilient) started. Target: Qwen3-Coder-30B max-speed.")
    while True:
        ensure_provisioned()
        try:
            redeploy()
        except SystemExit as e:
            log(f"redeploy hard failure (code {e.code}); recovering in 120s..."); time.sleep(120); continue
        except Exception as e:
            log("transient redeploy error:", repr(e), "- retry in 60s."); time.sleep(60); continue
        log("Entering keep-alive loop.")
        while True:
            time.sleep(900)
            if not session_exists():
                log("session lost (VM recycled). redeploying..."); break
            try:
                d = state()
                if d.get("_ok") and d.get("LLAMA_HEALTH") != "200":
                    log("llama unhealthy; redeploying..."); break
                execf("ping.py", timeout=60)
            except Exception as e:
                log("keepalive ping error:", repr(e))

main()