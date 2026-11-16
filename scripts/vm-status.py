import subprocess
print(open("/content/server.log", errors="replace").read()[-1800:])
print("=== DISK ===")
print(subprocess.run(["df","-h","/"],capture_output=True,text=True).stdout)
print("=== split dir size ===")
print(subprocess.run(["du","-sh","/content/airllm"],capture_output=True,text=True).stdout)
print("=== RAM ===")
print(subprocess.run(["free","-h"],capture_output=True,text=True).stdout)