import os
for f in ("/content/server.log", "/content/tunnel.log"):
    if os.path.exists(f):
        print(f"===== {f} =====")
        print(open(f, errors="replace").read()[-3500:])