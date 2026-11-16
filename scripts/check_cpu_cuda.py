import shutil, subprocess, os
print("nvcc:", shutil.which("nvcc"))
if shutil.which("nvcc"):
    print(subprocess.run(["nvcc","--version"],capture_output=True,text=True).stdout[-300:])
print("cuda dirs:", [d for d in ["/usr/local/cuda","/usr/local/cuda-12","/usr/local/cuda-13"] if os.path.isdir(d)])
r = subprocess.run(["bash","-c","ls /usr/local/ | grep -i cuda; ls /usr/lib/x86_64-linux-gnu/ | grep -E 'libcudart|libcublas' | head"],capture_output=True,text=True)
print(r.stdout)
print("nvidia-smi:", shutil.which("nvidia-smi"))