import subprocess, os, sys, time, glob
def sh(c): return subprocess.run(["bash","-c",c],capture_output=True,text=True).stdout

for _ in range(8):
    subprocess.run(["pkill","-9","-f","run_server_vram"])
    subprocess.run(["pkill","-9","-f","llama-server"])
    time.sleep(2)
    if not sh("pgrep -f 'run_server_vram|llama-server'").strip():
        break
print("remaining:", sh("pgrep -af 'run_server|llama-server'") or "(none)")
print("port 8000:", sh("ss -ltnp 2>/dev/null | grep :8000") or "(free)")

gguf = glob.glob("/content/gguf/*.gguf")
assert gguf, "no gguf found in /content/gguf"
model = gguf[0]
print("model:", model, f"{os.path.getsize(model)/1e9:.2f} GB")

binp = "/content/llama.cpp/build/bin/llama-server"
assert os.path.exists(binp), "llama-server binary missing"
env = dict(os.environ, PYTHONUNBUFFERED="1")
log = open("/content/llama.log","w")
args = [binp, "-m", model, "--host","0.0.0.0","--port","8000",
        "-ngl","99","-c","32768","--alias","qwen3-8b",
        "--flash-attn","auto","-np","1","--threads","2"]
p = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT, env=env, start_new_session=True)
print("started llama-server pid", p.pid)