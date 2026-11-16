"""Windows colab OAuth via a real subprocess stdin pipe (MSYS FIFO fails on win32).
Prints the genuine Google auth URL, then waits for the code in auth_code.txt.
"""
import subprocess, os, time, threading
CODE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "auth_code.txt")
if os.path.exists(CODE_FILE):
    os.remove(CODE_FILE)
env = dict(os.environ, PYTHONUNBUFFERED="1")
p = subprocess.Popen(["colab","--auth","oauth2","sessions"],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.STDOUT, text=True, env=env, bufsize=1)
def reader():
    for line in p.stdout:
        print(line.rstrip(), flush=True)
threading.Thread(target=reader, daemon=True).start()
print("WAITING_FOR_CODE: write the code to " + CODE_FILE, flush=True)
while True:
    if os.path.exists(CODE_FILE):
        code = open(CODE_FILE).read().strip()
        if code:
            p.stdin.write(code + "\n"); p.stdin.flush()
            print("CODE_SUBMITTED", flush=True)
            break
    if p.poll() is not None:
        print("PROCESS_EXITED_EARLY rc=", p.returncode, flush=True)
        break
    time.sleep(2)
p.wait()
print("AUTH_DONE rc=", p.returncode, flush=True)