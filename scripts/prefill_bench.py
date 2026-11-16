import urllib.request, json, time, uuid
from config import CHAT_URL, MODEL
URL = CHAT_URL
salt = uuid.uuid4().hex  # unique prefix -> forces full prefill, no KV reuse
filler = ("You are a helpful coding assistant. Follow the project conventions carefully. "
          "Prefer small, focused edits. Keep functions pure where possible. ")
target = int(__import__("sys").argv[1]) if len(__import__("sys").argv) > 1 else 21224
approx = target * 4.85  # ~chars/token observed for this text
reps = max(1, int(approx / len(filler)))
prompt = salt + " " + filler * reps + "\n\nReply with exactly the word OK."

body = {"model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 8, "temperature": 0, "stream": False}
req = urllib.request.Request(URL, data=json.dumps(body).encode(),
                             headers={"Content-Type": "application/json"})
t0 = time.time()
with urllib.request.urlopen(req, timeout=900) as r:
    j = json.loads(r.read().decode())
dt = time.time() - t0
u = j.get("usage", {})
pt = u.get("prompt_tokens", 0)
print(f"prompt_tokens={pt} | total={dt:.1f}s | implied prefill ~{pt/max(dt-0.6,0.1):.0f} tok/s | reply={j['choices'][0]['message']['content']!r}")