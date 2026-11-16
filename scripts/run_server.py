"""Qwen3-Coder-Next on Colab T4 via AirLLM, served as an OpenAI-compatible API.

Run on the VM:  nohup python /content/run_server.py > /content/server.log 2>&1 &
First run downloads + splits the checkpoint (~159GB streamed, ~45GB kept, 4bit).
"""
import os, sys, time, json, threading, uuid, queue

os.environ.setdefault("HF_HOME", "/content/hf")
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import torch
import airllm.utils as airutils

# T4 (sm75) has no bf16 kernels in bitsandbytes; quantize from fp16 instead.
_orig_compress = airutils.compress_layer_state_dict
def _compress_fp16(layer_state_dict, compression=None):
    if compression in ("4bit", "8bit"):
        layer_state_dict = {
            k: (v.to(torch.float16) if torch.is_tensor(v) and v.is_floating_point()
                and v.dtype != torch.float16 else v)
            for k, v in layer_state_dict.items()
        }
    return _orig_compress(layer_state_dict, compression)
airutils.compress_layer_state_dict = _compress_fp16

from airllm import AutoModel

MODEL_ID = "qwen3-coder-next"
HF_REPO = "Qwen/Qwen3-Coder-Next"
MAX_SEQ = 32768

print(f"[{time.strftime('%H:%M:%S')}] loading {HF_REPO} (4bit, delete_original)...", flush=True)
model = AutoModel.from_pretrained(
    HF_REPO,
    compression="4bit",
    delete_original=True,
    dtype=torch.float16,
    max_seq_len=MAX_SEQ,
    layer_shards_saving_path="/content/airllm",
)
tokenizer = model.tokenizer
print(f"[{time.strftime('%H:%M:%S')}] model ready", flush=True)

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
    try:
        return tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True,
                                             enable_thinking=False)
    except TypeError:
        return tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)

def _gen_kwargs(body, prompt):
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
                                        "owned_by": "colab-airllm"}]}

@app.post("/v1/chat/completions")
async def chat(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    stream = bool(body.get("stream"))
    prompt = _build_prompt(messages)
    kw = _gen_kwargs(body, prompt)
    cid = "chatcmpl-" + uuid.uuid4().hex[:24]
    created = int(time.time())
    n_prompt = len(tokenizer(prompt, return_tensors="pt")["input_ids"][0])

    if stream:
        def sse():
            base = {"id": cid, "object": "chat.completion.chunk",
                    "created": created, "model": MODEL_ID}
            # Immediate first byte so Cloudflare's origin-timeout never trips.
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
                                              kwargs=dict(kw, streamer=streamer), daemon=True)
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
                    yield ": keepalive\n\n"   # hold the tunnel open during slow steps
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
            out = model.generate(inputs["input_ids"].to(model.device), **kw)
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