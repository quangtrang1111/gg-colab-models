import airllm, os, inspect, glob
base = os.path.dirname(airllm.__file__)
print("airllm path:", base)
print("=== files ===")
for f in sorted(glob.glob(base + "/*.py")):
    print(" ", os.path.basename(f), os.path.getsize(f))
# find the compression + per-expert / streaming logic
import re
for f in sorted(glob.glob(base + "/*.py")):
    txt = open(f, encoding="utf-8", errors="replace").read()
    for kw in ["per_expert", "expert", "compress_layer_state_dict", "prefetch", "def run_layer", "streaming", "delete_original"]:
        for m in re.finditer(re.escape(kw), txt):
            ln = txt[:m.start()].count("\n") + 1
            line = txt.splitlines()[ln-1].strip()
            print(f"{os.path.basename(f)}:{ln}: {line[:140]}")
            break  # first occurrence per keyword per file