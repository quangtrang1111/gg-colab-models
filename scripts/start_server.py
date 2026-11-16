"""Launch run_server.py detached on the VM. Run via colab exec."""
import subprocess, os, sys

env = dict(os.environ,
           HF_HOME="/content/hf",
           HF_HUB_ENABLE_HF_TRANSFER="1",
           TOKENIZERS_PARALLELISM="false",
           PYTHONUNBUFFERED="1")
log = open("/content/server.log", "w")
p = subprocess.Popen([sys.executable, "/content/run_server.py"],
                     stdout=log, stderr=subprocess.STDOUT,
                     env=env, start_new_session=True)
print("server started, pid", p.pid)