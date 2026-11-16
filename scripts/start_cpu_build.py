import subprocess, sys
p = subprocess.Popen([sys.executable, "/content/cpu_compile_publish.py"],
                     stdout=open("/content/cpu_build.log", "w"), stderr=subprocess.STDOUT,
                     stdin=subprocess.DEVNULL, start_new_session=True)
print("cpu build pid", p.pid)