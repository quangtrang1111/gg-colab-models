# gg-colab-models

Serve a strong open-weight coding LLM on a **free Google Colab T4** and consume it from
[Command Code](https://github.com/quangtrang1111) as a BYOK "local" model — with no API key,
no local GPU requirement, and no spend.

Currently running: **Qwen3-Coder-30B-A3B-Instruct** (UD-IQ3_XXS) in **llama.cpp**, served
through a cloudflared tunnel with an OpenAI-compatible `/v1` API.

```
Command Code  ──►  cloudflared tunnel  ──►  Colab T4 (15 GB VRAM)
providers.json         (HTTPS)               └─ llama-server (llama.cpp, -ngl 99)
                                                   └─ Qwen3-Coder-30B-A3B UD-IQ3_XXS.gguf
```

---

## Quick start (Windows)

```bash
# 1. install the Colab CLI (cross-platform, no porting needed)
uv tool install google-colab-cli

# 2. authenticate (prints a Google URL; paste the code back)
colab --auth oauth2 sessions

# 3. deploy: provision a T4, download the prebuilt engine + model, serve, tunnel
python scripts/restorer_win.py
```

The restorer is **autonomous and self-healing**: it retries provisioning while the free
GPU quota is empty, redeploys end-to-end, rewrites the tunnel URL into Command Code's
`providers.json`, and then keeps the VM alive.

To point Command Code at it, `providers.json` should contain:

```json
{
  "provider": {
    "colab-t4": {
      "api": "openai-completions",
      "baseURL": "https://<random>.trycloudflare.com/v1",
      "name": "Colab T4 (llama.cpp)",
      "apiKey": false,
      "models": {
        "qwen3-coder-30b": {
          "name": "Qwen3-Coder-30B (Colab T4, 32K)",
          "contextWindow": 32768,
          "maxOutput": 4096,
          "reasoning": false,
          "cost": { "input": 0, "output": 0 }
        }
      }
    }
  }
}
```

---

## Why it is built this way

**1. AirLLM is the wrong engine on Colab.** AirLLM streams weights from disk and evicts
every layer back to `meta` after each token, so it re-reads the *entire* model per token.
Measured: **1176 s TTFT** for an 80B model. Colab's disk is ~214 MB/s against a T4's
~320 GB/s of VRAM bandwidth — a ~1500× gap. Usable speed requires the weights **resident
in VRAM**, which is why this project uses llama.cpp instead.

**2. Free Colab GPU quota is smaller than a compile.** Free GPU time arrives in ~10–15
minute bursts (`colab usage` hits `0.00`, then `colab new --gpu T4` fails with
`Service Unavailable`). But compiling llama.cpp with CUDA takes **~75–90 min** on a T4,
because the `fattn`/`mmq` CUDA template kernels dominate. A compile can therefore *never*
finish inside one free allotment, and the VM idle-recycles mid-build.

**The fix:** compile the engine **once** and publish it —
[`quangtrang/llama-server-colab-t4`](https://huggingface.co/quangtrang/llama-server-colab-t4)
— so every later VM just downloads it. A deploy drops from ~75 min of GPU time to **~4 min**,
which fits inside a free burst.

Compiling CUDA needs `nvcc` but **not a GPU**, so the engine was built on a *CPU-only*
Colab session (assignable even at a 0.00 GPU balance). The CUDA 12.6 runtime libraries are
bundled alongside the binary so it runs on a GPU VM regardless of that VM's CUDA version.

**3. VRAM decides the context size.** For this model (48 layers, 4 KV heads, head_dim 128)
the KV cache costs 49,152 values/token → **52,224 B/token at `q8_0`**, 27,648 B/token at
`q4_0`. Weights are 11,967 MiB and compute buffers ≈ 380 MiB, and the T4's *effective*
ceiling is ~14.5 GiB (not the 15,360 MiB `nvidia-smi` reports).

| context | KV types | VRAM | result |
|---|---|---|---|
| 32,768 | `q8_0` / `q8_0` | 13,979 MiB | works |
| **49,152** | **`q8_0` / `q4_0`** | **14,239 MiB** | **current config** |
| 65,536 | `q8_0` / `q4_0` | ~14,843 MiB | `CUDA error: the resource allocation failed` |

**4. Clients over-count tokens.** Command Code's accounting runs **~1.3×** llama.cpp's — it
sent 21,186 tokens while declaring 16,384, and 42,611 while declaring 32,768. So the
server's `n_ctx` must be **≥ 1.3 × the declared `contextWindow`**, or requests are rejected
with `request (N tokens) exceeds the available context size (M tokens)`.

**5. Prefill speed is set by the ubatch.** With quantized weights the ~12.85 GB is re-read
for *every* ubatch, so a 21K-token prompt at `-ub 256` means 83 ubatches (~1 TB of weight
traffic). Raising `-ub` cut prefill from 540 → 845 tok/s for +54 MiB per doubling.

**6. Your PC must stay awake.** The keep-alive runs on your machine; when it sleeps the VM
idle-recycles. The restorer calls `SetThreadExecutionState(ES_CONTINUOUS|ES_SYSTEM_REQUIRED)`
to prevent that.

---

## Measured results (Colab T4, UD-IQ3_XXS, 49,152 ctx)

| Metric | Value |
|---|---|
| VRAM | 14,401 MiB of 15,360 MiB |
| Decode | ~52 tok/s |
| Prefill | 845 tok/s (`-ub 1024`), 613 tok/s (`-ub 256`) |
| TTFT (small request) | ~1.9 s |
| Full deploy | ~4 min (quota → live endpoint) |
| First message of a session | ~28 s (21K-token system prompt must be prefilled once) |
| Subsequent messages | ~0.6 s (KV prefix is reused) |

---

## Repo layout

Everything lives in `scripts/`. Scripts are split into two groups: **VM-side** (uploaded to
Colab and run there) and **local** (run on your machine).

### VM-side

| Script | Role |
|---|---|
| `build_30b.py` | download the GGUF + fetch the prebuilt engine (falls back to compiling) |
| `start_30b.py` | launch `llama-server` with the tuned T4 flags |
| `start_tunnel.py` | launch the cloudflared quick tunnel |
| `setup_llama_vm.py` | install `huggingface_hub` + `cloudflared` |
| `start_build_30b.py` | detached launcher for the build |
| `vm_state.py` | report build / server / tunnel state to the restorer |
| `ping.py` | keep-alive ping (counts as kernel activity) |
| `cpu_compile_publish.py` | build the engine on a **CPU-only** session and publish it to HF |
| `start_cpu_build.py`, `cpu_state.py` | detached launcher + state probe for the above |

### Local

| Script | Role |
|---|---|
| `restorer_win.py` | autonomous restorer (Windows) — provision, deploy, keep alive, self-heal |
| `restorer.py` | same, for WSL |
| `cpu_watcher.py` | drive the CPU-session build; keeps the PC awake |
| `auth_win.py` | Windows OAuth helper (MSYS FIFOs can't feed native `colab.exe` stdin) |
| `config.py` | shared config — resolves the tunnel URL / model / providers path |
| `code-test.py` | coding benchmark (TTFT, decode rate) |
| `verify_32k.py` | large-context test (sends a ~44K-token prompt) |
| `prefill_bench.py` | prefill throughput benchmark (forces a full prefill) |
| `speed-test.py`, `stream-test.py`, `translate-test.py` | misc. latency / streaming / EN→VI tests |
| `bundle_test.py` | verify the published HF bundle is self-contained (`ldd` check) |
| `upload_readme.py` | publish the HF repo card |
| `ctx_check.py`, `buf_check.py`, `mib_check.py`, `req_timing.py`, `llama_log_check.py` | diagnostics |

---

## Configuration

No secrets are committed. Override via environment variables:

| Variable | Purpose |
|---|---|
| `TUNNEL_URL` | base URL of the server (default: read from `providers.json`, else `http://127.0.0.1:8000`) |
| `MODEL` | model id (default: read from `providers.json`, else `qwen3-coder-30b`) |
| `COMMAND_CODE_PROVIDERS` | path to Command Code's `providers.json` (auto-detected) |
| `HF_TOKEN` | Hugging Face **write** token — only needed to publish the engine bundle |

```bash
TUNNEL_URL=https://xyz.trycloudflare.com python scripts/code-test.py
```

---

## Operational notes

- **The tunnel URL changes on every redeploy** (cloudflared quick tunnels are anonymous), so
  the restorer rewrites `providers.json` automatically.
- **`colab exec` has a 30 s silence timeout** — pass `--timeout N` for slow cells, and run
  one exec at a time (cells are serial; concurrent execs drop with "Connection was lost").
- **`colab exec` has no `-c` inline flag** — use `-f <file>`.
- **Always verify the prebuilt binary with `--list-devices`, not `--version`.** `--version`
  succeeds even when the CUDA libraries can't load, so a broken bundle silently falls back
  to a 75-minute compile. `--list-devices` must print `CUDA`.
- **From Git Bash**, prefix commands with `MSYS_NO_PATHCONV=1` or `/content/...` paths get
  mangled into Windows paths.
- **Non-ASCII output crashes the Windows console** during `colab exec`; the state probes
  sanitize to ASCII.

---

## License

MIT — see [LICENSE](LICENSE).

The prebuilt engine published to Hugging Face contains llama.cpp / ggml (MIT, © ggml-org)
and NVIDIA CUDA runtime libraries (NVIDIA CUDA Toolkit EULA).
