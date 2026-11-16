import subprocess, os
def sh(c): return subprocess.run(["bash","-c",c],capture_output=True,text=True).stdout
print("BUILD_ALIVE:", bool(sh("pgrep -f cpu_compile_publish.py").strip()))
done = os.path.exists("/content/llama.cpp/build/bin/llama-server")
print("BUILD_DONE:", done)
pub = os.path.exists("/content/cpu_build.log") and "PUBLISHED:" in open("/content/cpu_build.log").read()
print("PUBLISHED:", pub)
print("BUILD_TAIL:", sh("tail -3 /content/cpu_build.log").encode("ascii","replace").decode().replace(chr(10)," "))