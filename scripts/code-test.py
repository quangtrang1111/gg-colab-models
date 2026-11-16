import urllib.request, json, time
from config import CHAT_URL, MODEL
url = CHAT_URL
body = {"model":MODEL,
        "messages":[{"role":"user","content":"Write a Python function merge_sorted(a, b) that merges two sorted lists into one sorted list in O(n+m) time. Then show a quick example call."}],
        "max_tokens":400, "temperature":0, "stream":True}
req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type":"application/json"})
t0=time.time(); first=None; n=0; text=""; last=t0
with urllib.request.urlopen(req, timeout=300) as r:
    for raw in r:
        line=raw.decode().strip()
        if not line.startswith("data:"): continue
        data=line[5:].strip()
        if data=="[DONE]": break
        try: j=json.loads(data)
        except: continue
        delta=j["choices"][0]["delta"].get("content")
        if delta:
            now=time.time()
            if first is None: first=now-t0
            n+=1; text+=delta; last=now
total=time.time()-t0
gen=max(last-(t0+(first or 0)),1e-6)
rate=(n-1)/gen if n>1 else 0
print(f"TTFT {(first or 0):.2f}s | chunks {n} | total {total:.2f}s | decode {rate:.1f} tok/s", flush=True)
print("---- output ----", flush=True)
print(text, flush=True)