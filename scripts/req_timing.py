import subprocess, os, re
def sh(c): return subprocess.run(["bash","-c",c],capture_output=True,text=True).stdout
def a(s): return s.encode("ascii","replace").decode()
log = open("/content/llama.log", errors="replace").read() if os.path.exists("/content/llama.log") else ""
lines = log.splitlines()
print("--- prompt/eval/timing/slot lines ---")
pat = re.compile(r"prompt processing|prompt eval time|eval time =|total time|n_past|slot launch|release:|tokens per second|n_tokens =", re.I)
for l in lines:
    if pat.search(l):
        print(" ", a(l).strip()[:185])
print("--- errors ---")
for l in lines:
    if re.search(r"error|exceed", l, re.I):
        print(" ", a(l).strip()[:185])