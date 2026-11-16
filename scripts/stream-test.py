import urllib.request, json, time

from config import CHAT_URL
url = CHAT_URL
body = {"model": "qwen3-coder-next",
        "messages": [{"role": "user", "content": "Count from 1 to 5."}],
        "max_tokens": 5, "temperature": 0, "stream": True}
req = urllib.request.Request(url, data=json.dumps(body).encode(),
                             headers={"Content-Type": "application/json"})
t0 = time.time(); first = None; n = 0; text = ""
with urllib.request.urlopen(req, timeout=900) as r:
    for raw in r:
        line = raw.decode().strip()
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            break
        try:
            j = json.loads(data)
        except Exception:
            continue
        delta = j["choices"][0]["delta"].get("content")
        if delta:
            if first is None:
                first = time.time() - t0
            n += 1; text += delta
            print(f"[{time.time()-t0:6.1f}s] {delta!r}", flush=True)
print(f"TTFT {first:.1f}s | chunks {n} | total {time.time()-t0:.1f}s | text={text!r}", flush=True)