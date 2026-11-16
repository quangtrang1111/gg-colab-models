base = "/usr/local/lib/python3.13/dist-packages/airllm/"
b = open(base + "airllm_base.py").read().splitlines()
print("===== base 688-770: cpu_resident + mmap embedding =====")
for i in range(687, 770):
    print(f"{i+1}: {b[i]}")
print("\n===== grep repo id / Flash-Next / compression guards across package =====")
import glob, re
for f in sorted(glob.glob(base + "*.py")):
    txt = open(f, encoding="utf-8", errors="replace").read()
    for kw in ["Flash-Next", "Qwen3.8", "Qwen4Exp", "repo_id", "Qwen/", "compression is not None", "compression is None", "mmap", "cpu_resident_marker"]:
        for m in re.finditer(re.escape(kw), txt):
            ln = txt[:m.start()].count("\n") + 1
            print(f"{f.split('/')[-1]}:{ln}: {txt.splitlines()[ln-1].strip()[:130]}")
            break