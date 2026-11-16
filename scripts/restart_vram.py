import subprocess, os, sys, time

def sh(cmd):
    return subprocess.run(["bash","-c",cmd], capture_output=True, text=True).stdout

# 1. Free disk: remove the old AirLLM split (our scratch artifact, ~42GB).
print("before:", sh("df -h / | tail -1"))
sh("rm -rf /content/airllm")
print("after rm airllm:", sh("df -h / | tail -1"))

# 2. Fast downloader for the ~28GB checkpoint.
print(sh("pip install -q hf_transfer 2>&1 | tail -2"))

# 3. Force-kill any old server (AirLLM run_server.py or prior vram) until gone.
for _ in range(8):
    subprocess.run(["pkill","-9","-f","run_server"])
    time.sleep(2)
    if not subprocess.run(["pgrep","-f","run_server"],capture_output=True,text=True).stdout.strip():
        break
print("remaining server procs:", sh("pgrep -af run_server") or "(none)")
print("port 8000:", sh("ss -ltnp 2>/dev/null | grep :8000") or "(free)")

# 4. Start the resident-VRAM server detached.
env = dict(os.environ, HF_HOME="/content/hf", HF_HUB_ENABLE_HF_TRANSFER="1",
           TOKENIZERS_PARALLELISM="false", PYTHONUNBUFFERED="1")
log = open("/content/server.log","w")
p = subprocess.Popen([sys.executable,"/content/run_server_vram.py"],
                     stdout=log, stderr=subprocess.STDOUT, env=env, start_new_session=True)
print("started VRAM server pid", p.pid)