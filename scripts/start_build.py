import subprocess, os, sys
env = dict(os.environ, HF_HOME="/content/hf", HF_HUB_ENABLE_HF_TRANSFER="1", PYTHONUNBUFFERED="1")
log = open("/content/build.log","w")
p = subprocess.Popen([sys.executable,"/content/build_llama.py"],
                     stdout=log, stderr=subprocess.STDOUT, env=env, start_new_session=True)
print("started build pid", p.pid)