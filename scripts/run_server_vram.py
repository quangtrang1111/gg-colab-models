"""Qwen2.5-Coder-14B-Instruct on Colab T4, weights resident in VRAM (4bit NF4).

Unlike AirLLM (which streams every layer from disk per token), this loads the whole
model into the T4's 16GB VRAM once and keeps it there -> normal GPU decode speed.
Run on the VM:  python /content/run_server_vram.py > /content/server.log 2>&1 &
"""
import os, sys, time, json, threading, uuid, queue

os.environ.setdefault("HF_HOME", "/content/hf")
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

MODEL_ID = "qwen2.5-coder-14b"
HF_REPO = "Qwen/Qwen2.5-Coder-14B-Instruct"
MAX_SEQ = 16384  # 4bit weights ~10GB + 16K KV cache ~3.2GB fits the T4's 15GB

print(f"[{time.strftime('%H:%M:%S')}] loading {HF_REPO} (4bit NF4, resident VRAM)...", flush=True)
bnb = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,   # T4 (sm75) has no bf16 kernels
    bnb_4bit_use_double_quant=True,
)
model = AutoModelForCausalLM.from_pretrained(
    HF_REPO,
    quantization_config=bnb,
    device_map="cuda:0",
    torch_dtype=torch.float16,
    attn_implementation="sdpa",
)
model.eval()
tokenizer = AutoTokenizer.from_pretrained(HF_REPO)
print(f"[{time.strftime('%H:%M:%S')}] model ready on {model.device}", flush=True)

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from transformers import TextIteratorStreamer
import uvicorn

app = FastAPI()
gen_lock = threading.Lock()

def _text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(p.get("text", "") for p in content if isinstance(p, dict))
    return str(content)

def _build_prompt(messages):
    msgs = [{"role": m["role"], "content": _text(m.get("content", ""))} for m in messages]
    return tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)

def _gen_kwargs(body):
    max_new = min(int(body.get("max_tokens") or 512), 4096)
    temp = body.get("temperature")
    kw = dict(max_new_tokens=max_new, use_cache=True, return_dict_in_generate=True)
    if temp is not None and float(temp) > 0:
        kw.update(do_sample=True, temperature=float(temp),
                  top_p=float(body.get("top_p") or 0.95))
    else:
        kw.update(do_sample=False)
    return kw

@app.get("/health")
def health():
    return {"ok": True, "model": MODEL_ID}

@app.get("/v1/models")
def models():
    return {"object": "list", "data": [{"id": MODEL_ID, "object": "model",
                                        "owned_by": "colab-t4"}]}

@app.post("/v1/chat/completions")
async def chat(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    stream = bool(body.get("stream"))
    prompt = _build_prompt(messages)
    kw = _gen_kwargs(body)
    cid = "chatcmpl-" + uuid.uuid4().hex[:24]
    created = int(time.time())
    n_prompt = len(tokenizer(prompt, return_tensors="pt")["input_ids"][0])

    if stream:
        def sse():
            base = {"id": cid, "object": "chat.completion.chunk",
                    "created": created, "model": MODEL_ID}
            yield f"data: {json.dumps({**base, 'choices': [{'index': 0, 'delta': {'role': 'assistant'}, 'finish_reason': None}]})}\n\n"
            q = queue.Queue()
            def worker():
                try:
                    with gen_lock:
                        streamer = TextIteratorStreamer(tokenizer, skip_prompt=True,
                                                        skip_special_tokens=True)
                        inputs = tokenizer(prompt, return_tensors="pt", truncation=True,
                                           max_length=MAX_SEQ - kw["max_new_tokens"])
                        th = threading.Thread(target=model.generate,
                                              args=(inputs["input_ids"].to(model.device),),
                                              kwargs=dict(kw, streamer=streamer,
                                                          attention_mask=inputs["attention_mask"].to(model.device)),
                                              daemon=True)
                        th.start()
                        for piece in streamer:
                            q.put(("delta", piece))
                        th.join()
                    q.put(("done", None))
                except Exception as e:
                    q.put(("error", str(e)))
            threading.Thread(target=worker, daemon=True).start()
            n = 0
            while True:
                try:
                    kind, val = q.get(timeout=20)
                except queue.Empty:
                    yield ": keepalive\n\n"
                    continue
                if kind == "delta":
                    n += 1
                    yield f"data: {json.dumps({**base, 'choices': [{'index': 0, 'delta': {'content': val}, 'finish_reason': None}]})}\n\n"
                elif kind == "error":
                    yield f"data: {json.dumps({**base, 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}], 'error': val})}\n\n"
                    break
                else:
                    break
            yield f"data: {json.dumps({**base, 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}], 'usage': {'prompt_tokens': n_prompt, 'completion_tokens': n, 'total_tokens': n_prompt + n}})}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(sse(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache",
                                          "X-Accel-Buffering": "no"})

    def run_sync():
        with gen_lock:
            inputs = tokenizer(prompt, return_tensors="pt", truncation=True,
                               max_length=MAX_SEQ - kw["max_new_tokens"])
            out = model.generate(inputs["input_ids"].to(model.device),
                                 attention_mask=inputs["attention_mask"].to(model.device), **kw)
            seq = out.sequences[0][inputs["input_ids"].shape[1]:]
            return tokenizer.decode(seq, skip_special_tokens=True), len(seq)

    from fastapi.concurrency import run_in_threadpool
    try:
        text, n = await run_in_threadpool(run_sync)
    except Exception as e:
        return JSONResponse({"error": {"message": str(e), "type": "server_error"}},
                            status_code=500)
    return {"id": cid, "object": "chat.completion", "created": created,
            "model": MODEL_ID,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": text},
                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": n_prompt, "completion_tokens": n,
                      "total_tokens": n_prompt + n}}

if __name__ == "__main__":
    print(f"[{time.strftime('%H:%M:%S')}] serving on :8000", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")