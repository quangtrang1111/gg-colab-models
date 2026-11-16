import subprocess, os, sys, time

for _ in range(6):
    subprocess.run(["pkill", "-9", "-f", "run_server.py"])
    time.sleep(2)
    r = subprocess.run(["pgrep", "-f", "run_server.py"], capture_output=True, text=True)
    if not r.stdout.strip():
        break
print("remaining run_server procs:",
      subprocess.run(["pgrep", "-af", "run_server.py"], capture_output=True, text=True).stdout or "(none)")

env = dict(os.environ, HF_HOME="/content/hf", HF_HUB_ENABLE_HF_TRANSFER="1",
           TOKENIZERS_PARALLELISM="false", PYTHONUNBUFFERED="1")
log = open("/content/server.log", "w")
p = subprocess.Popen([sys.executable, "/content/run_server.py"],
                     stdout=log, stderr=subprocess.STDOUT, env=env, start_new_session=True)
print("started clean server pid", p.pid)