"""Start llama-server for Qwen3-Coder-30B-A3B, max-speed T4 config.
UD-IQ3_XXS (~12GB) + q8_0 KV at 32K (~1.6GB) fits fully in 16GB VRAM -> -ngl 99,
no CPU offload, and 32K context for Command Code's large prompts. Flash attention on.
"""
import subprocess, os, sys, time, glob
def sh(c): return subprocess.run(["bash","-c",c],capture_output=True,text=True).stdout

for _ in range(8):
    subprocess.run(["pkill","-9","-f","llama-server"])
    time.sleep(2)
    if not sh("pgrep -f 'llama-server'").strip():
        break
print("remaining:", sh("pgrep -af 'llama-server'") or "(none)")
print("port 8000:", sh("ss -ltnp 2>/dev/null | grep :8000") or "(free)")

gguf = glob.glob("/content/gguf/**/*.gguf", recursive=True)
assert gguf, "no gguf found in /content/gguf"
iq3 = [g for g in gguf if "iq3" in g.lower()]
model = iq3[0] if iq3 else gguf[0]
print("model:", model, f"{os.path.getsize(model)/1e9:.2f} GB")

binp = "/content/llama.cpp/build/bin/llama-server"
assert os.path.exists(binp), "llama-server binary missing"
BUILD = "/content/llama.cpp/build"
ld = os.pathsep.join([f"{BUILD}/bin", f"{BUILD}/lib", os.environ.get("LD_LIBRARY_PATH", "")])
env = dict(os.environ, PYTHONUNBUFFERED="1", LD_LIBRARY_PATH=ld)
log = open("/content/llama.log","w")
args = [binp, "-m", model, "--host","0.0.0.0","--port","8000",
        "-ngl","99","-c","49152","--alias","qwen3-coder-30b",
        "--cache-type-k","q8_0","--cache-type-v","q4_0",
        "-fa","on","-b","2048","-ub","1024","-np","1","--threads","2"]
p = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT, env=env, start_new_session=True)
print("started llama-server pid", p.pid)