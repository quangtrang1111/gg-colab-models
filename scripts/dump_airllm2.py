base = "/usr/local/lib/python3.13/dist-packages/airllm/"
print("===== airllm_qwen4_exp.py (FULL) =====")
print(open(base + "airllm_qwen4_exp.py").read())
b = open(base + "airllm_base.py").read().splitlines()
print("\n===== base: function defs + expert/compression/persister mentions =====")
import re
for i, l in enumerate(b):
    if re.search(r"def |expert_prefix|_setup_expert|_expert_streaming|SafetensorModelPersister|compression|layer_names_dict\s*=|expert_streaming", l):
        print(f"{i+1}: {l[:150]}")