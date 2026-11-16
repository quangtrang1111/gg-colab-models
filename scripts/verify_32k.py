import urllib.request, json, time

from config import CHAT_URL, MODEL
URL = CHAT_URL

# ~23K-token prompt (above the 21186 that previously overflowed 8K, below 32768).
# Each filler repeat is ~25 tokens; 1750 repeats ~= 44K tokens (exceeds Command Code 42611).
filler = ("You are a helpful coding assistant. Follow the project conventions carefully. "
          "Prefer small, focused edits. Keep functions pure where possible. ")
block = filler * 1750
prompt = block + "\n\nNow reply with exactly the word OK and nothing else."

body = {"model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 50, "temperature": 0, "stream": False}

print(f"prompt chars: {len(prompt)} (~{len(prompt)//4} tokens)", flush=True)
req = urllib.request.Request(URL, data=json.dumps(body).encode(),
                             headers={"Content-Type": "application/json"})
t0 = time.time()
try:
    with urllib.request.urlopen(req, timeout=600) as r:
        j = json.loads(r.read().decode())
    dt = time.time() - t0
    usage = j.get("usage", {})
    text = j["choices"][0]["message"]["content"]
    print(f"STATUS OK in {dt:.1f}s | prompt_tokens={usage.get('prompt_tokens')} "
          f"completion_tokens={usage.get('completion_tokens')}", flush=True)
    print(f"reply: {text!r}", flush=True)
    if usage.get("prompt_tokens", 0) > 21186:
        print("LARGE-CONTEXT PASS: accepted a prompt bigger than the old 8K failure.", flush=True)
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code}: {e.read().decode()[:500]}", flush=True)
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}", flush=True)