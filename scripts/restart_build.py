import subprocess, time
subprocess.run(["pkill", "-9", "-f", "build_30b.py"])
time.sleep(2)
subprocess.run(["rm", "-f", "/content/build.log"])
r = subprocess.run(["python3", "/content/start_build_30b.py"], capture_output=True, text=True)
print("restart:", r.stdout.strip(), r.stderr.strip()[:200])
print("alive:", subprocess.run(["bash","-c","pgrep -af build_30b.py"],capture_output=True,text=True).stdout.strip()[:120])