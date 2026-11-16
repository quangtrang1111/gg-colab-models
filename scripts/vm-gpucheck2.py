import subprocess, time, os
print("=== nvidia-smi ===")
print(subprocess.run(["nvidia-smi","--query-gpu=utilization.gpu,memory.used,temperature.gpu","--format=csv"],capture_output=True,text=True).stdout)
print(subprocess.run(["nvidia-smi","--query-compute-apps=pid,used_memory","--format=csv"],capture_output=True,text=True).stdout)
# measure sequential read throughput from the split model dir
import glob
files = sorted(glob.glob("/content/airllm/splitted_model.4bit/*"))
print("=== split files (first 6) ===")
for f in files[:6]:
    print(f"  {os.path.basename(f)}  {os.path.getsize(f)/1e9:.2f} GB")
# time reading 1GB from a large shard
big = max(files, key=lambda f: os.path.getsize(f)) if files else None
if big:
    t0=time.time(); n=0
    with open(big,"rb") as fh:
        while n < 1_000_000_000:
            b=fh.read(8_000_000)
            if not b: break
            n+=len(b)
    dt=time.time()-t0
    print(f"=== read {n/1e9:.2f} GB in {dt:.2f}s = {n/1e6/dt:.0f} MB/s ===")
print("=== server.log tail ===")
print(open("/content/server.log").read()[-1200:])