base = "/usr/local/lib/python3.13/dist-packages/airllm/"
print("===== airllm_qwen4_exp.py =====")
print(open(base + "airllm_qwen4_exp.py").read())
print("\n===== airllm_base.py lines 330-420 =====")
lines = open(base + "airllm_base.py").read().splitlines()
for i in range(329, 420):
    print(f"{i+1}: {lines[i]}")
print("\n===== airllm_base.py lines 790-880 =====")
for i in range(789, 880):
    print(f"{i+1}: {lines[i]}")