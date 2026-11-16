import subprocess, os, re
def sh(c): return subprocess.run(["bash","-c",c],capture_output=True,text=True).stdout
def a(s): return s.encode("ascii","replace").decode()
log = open("/content/llama.log", errors="replace").read() if os.path.exists("/content/llama.log") else ""
print("--- MiB / buffer / size lines ---")
for l in log.splitlines():
    if re.search(r"MiB|buffer|KV|cache|allocat", l, re.I):
        print(" ", a(l).strip()[:175])
print("--- last 12 lines ---")
for l in log.splitlines()[-12:]:
    print(" ", a(l).strip()[:175])