import urllib.request, json, time
print("HEALTH:", urllib.request.urlopen("http://localhost:8000/health", timeout=10).read().decode())
body = {"model": "qwen3-coder-next",
        "messages": [{"role": "user", "content": "Reply with exactly one word: hello"}],
        "max_tokens": 6, "temperature": 0, "stream": False}
t = time.time()
req = urllib.request.Request("http://localhost:8000/v1/chat/completions",
                             data=json.dumps(body).encode(),
                             headers={"Content-Type": "application/json"})
r = urllib.request.urlopen(req, timeout=900).read().decode()
print("elapsed %.1fs" % (time.time() - t))
print(r)