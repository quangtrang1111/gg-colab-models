import subprocess, shutil, os
def sh(c): return subprocess.run(["bash","-c",c],capture_output=True,text=True).stdout
print("nvcc:", shutil.which("nvcc"))
print(sh("nvcc --version 2>/dev/null | tail -2"))
print("cmake:", shutil.which("cmake"), "| gcc:", shutil.which("gcc"), "| g++:", shutil.which("g++"), "| git:", shutil.which("git"))
print("cuda dirs:", sh("ls -d /usr/local/cuda* 2>/dev/null"))
print("nproc:", sh("nproc").strip())
print("=== disk ==="); print(sh("df -h / | tail -1"))
print("=== GPU ==="); print(sh("nvidia-smi --query-gpu=memory.used,memory.total --format=csv"))
print("=== current server proc ==="); print(sh("pgrep -af 'llama-server' ") or "(none)")
print("=== pip llama/ctranslate2 ==="); print(sh("pip list 2>/dev/null | grep -iE 'llama|ctranslate2|cmake'") or "(none)")