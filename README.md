# gg-colab-models

Serve a strong open-weight coding LLM on a **free Google Colab T4** and consume it from
**any OpenAI-compatible client** — no API key, no local GPU, no spend.

Currently running: **Qwen3-Coder-30B-A3B-Instruct** (UD-IQ3_XXS) in **llama.cpp**, served
through a cloudflared tunnel with an OpenAI-compatible `/v1` API.

```
Your AI client  ──►  cloudflared tunnel  ──►  Colab T4 (15 GB VRAM)
(OpenAI API)              (HTTPS)               └─ llama-server (llama.cpp, -ngl 99)
                                                    └─ Qwen3-Coder-30B-A3B UD-IQ3_XXS.gguf
```

Because the endpoint is plain OpenAI `/v1`, it plugs into IDE agents, chat UIs, SDKs and
CLI tools alike. **Command Code** is the client this setup was developed and tested
against — see [Connect a client](#connect-a-client) for the others.

### Links

| | |
|---|---|
| **This repo** | [github.com/quangtrang1111/gg-colab-models](https://github.com/quangtrang1111/gg-colab-models) |
| **Prebuilt engine** | [huggingface.co/quangtrang/llama-server-colab-t4](https://huggingface.co/quangtrang/llama-server-colab-t4) — the `llama-server` binary + CUDA runtime libs (public, anonymous download) |
| **Model weights** | [huggingface.co/unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF](https://huggingface.co/unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF) — `UD-IQ3_XXS` GGUF, 12.85 GB |
| **Colab CLI** | [github.com/googlecolab/google-colab-cli](https://github.com/googlecolab/google-colab-cli) — cross-platform CLI this project drives |

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
GPU quota is empty, redeploys end-to-end, rewrites the tunnel URL into the client configs
it finds, and then keeps the VM alive.

---

## Connect a client

The endpoint speaks the OpenAI API, so any client that accepts a custom base URL can use
it. Register it as an OpenAI-compatible provider with:

| Setting | Value |
|---|---|
| Base URL | `https://<random>.trycloudflare.com/v1` — printed by the restorer, and rewritten automatically on every redeploy |
| API key | none; the server does not require one |
| Model id | `qwen3-coder-30b` |
| Context window | 35,000 tokens (the server itself holds 49,152) |

### Command Code — the tested client

Register a BYOK provider in `~/.commandcode/providers.json`:

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
          "name": "Qwen3-Coder-30B (Colab T4, 48K)",
          "contextWindow": 35000,
          "maxOutput": 4096,
          "reasoning": false,
          "cost": { "input": 0, "output": 0 }
        }
      }
    }
  }
}
```

The restorer keeps this file's `baseURL` in sync on every redeploy.

### Other clients

| Client | Where the base URL goes |
|---|---|
| Continue | `~/.continue/config.json` → `models[].apiBase` |
| Aider | `~/.aider.conf.yml` → `OPENAI_API_BASE` |
| Cline / Roo Code (VS Code) | settings → OpenAI Compatible → Base URL |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` |
| LiteLLM proxy | `~/.config/litellm/config.yaml` → `model_list[].api_base` |
| Open WebUI | Admin → Connections → OpenAI → Base URL |
| Cursor | `~/.cursor/mcp.json` |
| Any OpenAI SDK | `base_url=` / `OPENAI_BASE_URL` |

The restorer rewrites the tunnel URL in the Command Code, Continue, Aider, LiteLLM,
Cursor, Windsurf and VS Code extension configs that exist on this machine. For anything
else, either point the client at a stable URL you control, or add its config path to the
`CLIENT_CONFIGS` environment variable so the restorer keeps it in sync too.

---

## Why it is built this way

**1. The weights must be resident in VRAM.** Any engine that streams weights from disk and
evicts them between tokens re-reads the *entire* model per token — one such
disk-streaming approach measured **1176 s TTFT** for an 80B model here. Colab's disk is
~214 MB/s against a T4's ~320 GB/s of VRAM bandwidth — a ~1500× gap. Usable interactive
speed therefore requires the weights **resident in VRAM**, which is why this project uses
llama.cpp with full GPU offload (`-ngl 99`).

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

**4. Client token accounting does not match the server's.** A client's own tokenizer, or
its estimate of the conversation, can differ from llama.cpp's — so it may send more tokens
than it thinks it has. Measured with Command Code: **~1.3×** — it sent 21,186 tokens while
declaring 16,384, and 42,611 while declaring 32,768. Requests beyond the server's
`n_ctx` are rejected with
`request (N tokens) exceeds the available context size (M tokens)`.

So the server's `n_ctx` must be **≥ 1.3 × the declared `contextWindow`** of whichever
client you use. That is why the *declared* window (`contextWindow: 35000` → ≈45,500 real
tokens) is kept below the server's 49,152 capacity, and why the display name says **48K**
while the client window is 35K: the 48K is what the **server** can hold, and the client is
deliberately capped lower so its over-count still fits.

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
| `config.py` | shared config — resolves the tunnel URL / model / client config path |
| `client_urls.py` | knows where OpenAI-compatible clients keep their base URL and keeps them in sync when the tunnel changes |
| `code-test.py` | coding benchmark (TTFT, decode rate) |
| `verify_32k.py` | large-context test (sends a ~46K-token prompt, above the 35K declared window × 1.3) |
| `prefill_bench.py` | prefill throughput benchmark (forces a full prefill) |
| `translate-test.py` | EN→VI translation test (the original use case for this setup) || `bundle_test.py` | verify the published HF bundle is self-contained (`ldd` check) |
| `upload_readme.py` | publish the HF repo card |
| `ctx_check.py`, `buf_check.py`, `mib_check.py`, `req_timing.py`, `llama_log_check.py` | diagnostics |
| `diag_30b.py`, `check_tunnel.py`, `tunnel_diag.py`, `cpu_diag.py` | VM-side diagnostics (server log, tunnel, processes) |
| `restart_build.py` | restart the build on the VM (picks up an updated build script) |
| `dl_iq3.py` | download the IQ3_XXS GGUF directly from the unsloth repo |
| `check_build_env.py`, `check_cpu_cuda.py` | build-environment / CUDA-toolkit checks (used on the CPU session) |
| `colab-new.sh`, `colab-auth.sh`, `colab-auth-win.sh` | WSL helpers for the Colab CLI |

---

## Configuration

No secrets are committed. Override via environment variables:

| Variable | Purpose |
|---|---|
| `TUNNEL_URL` | base URL of the server (default: a tunnel URL found in any known client config, else `http://127.0.0.1:8000`) |
| `MODEL` | model id (default: read from Command Code's `providers.json`, else `qwen3-coder-30b`) |
| `CLIENT_CONFIGS` | extra client config paths/globs to read from and keep in sync (os.pathsep-separated) |
| `COMMAND_CODE_PROVIDERS` | path to Command Code's `providers.json` (auto-detected) |
| `HF_TOKEN` | Hugging Face **write** token — only needed to publish the engine bundle |

```bash
TUNNEL_URL=https://xyz.trycloudflare.com python scripts/code-test.py
```

---

## Operational notes

- **The tunnel URL changes on every redeploy** (cloudflared quick tunnels are anonymous), so
  the restorer rewrites it in every known client config it finds on this machine — see
  [Connect a client](#connect-a-client).
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
