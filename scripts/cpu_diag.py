import subprocess, os
def sh(c): return subprocess.run(["bash","-c",c],capture_output=True,text=True).stdout
def a(s): return s.encode("ascii","replace").decode()
print("ALIVE:", bool(sh("pgrep -f cpu_compile_publish.py").strip()))
print("LOG_TAIL:", a(sh("tail -6 /content/cpu_build.log")).replace(chr(10)," | "))
print("BUNDLE:", a(sh("ls -la /content/llama-server-cuda-sm75.tar.gz 2>/dev/null")))
print("STAGE:", a(sh("du -sh /content/bundle 2>/dev/null")))