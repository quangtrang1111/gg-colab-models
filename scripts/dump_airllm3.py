base = "/usr/local/lib/python3.13/dist-packages/airllm/"
b = open(base + "airllm_base.py").read().splitlines()
print("===== generic set_layer_names_dict (base 78-83) =====")
for i in range(77, 83):
    print(f"{i+1}: {b[i]}")
print("\n===== auto_model.py (FULL dispatch) =====")
print(open(base + "auto_model.py").read())
print("\n===== __init__.py (FULL exports) =====")
print(open(base + "__init__.py").read())
u = open(base + "utils.py").read().splitlines()
print("\n===== utils.py: persister selection =====")
import re
for i, l in enumerate(u):
    if re.search(r"class .*Persister|def get_model_persister|SafetensorModelPersister|compression|def load_layer_subset|def layer_tensor_names", l):
        print(f"{i+1}: {l[:150]}")