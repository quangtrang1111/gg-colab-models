---
license: mit
library_name: llama.cpp
tags:
  - llama.cpp
  - gguf
  - cuda
  - colab
  - t4
  - qwen3-coder
  - prebuilt-binary
---

# llama-server for Colab T4 (prebuilt, CUDA sm75)

Prebuilt **llama.cpp inference engine** for serving GGUF models on a **Google Colab T4**
(compute capability 7.5), plus the **CUDA 12 runtime libraries** it needs.

This repo contains the **engine only**. The model weights (Qwen3-Coder-30B-A3B GGUF) are
**not** here — they live in
[`unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF`](https://huggingface.co/unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF)
(`Qwen3-Coder-30B-A3B-Instruct-UD-IQ3_XXS.gguf`, 12.85 GB).

> **Project & full scripts:** [github.com/quangtrang1111/gg-colab-models](https://github.com/quangtrang1111/gg-colab-models)
> — the complete toolkit that deploys this engine on a free Colab T4 and exposes it as a
> standard OpenAI-compatible `/v1` endpoint, usable from **any** AI client (IDE agents,
> chat UIs, SDKs, CLI tools). Command Code is the client it was developed and tested
> against. Includes an autonomous restorer, benchmarks and diagnostics.

---

## What is in here

| File | Size | Contents |
|---|---|---|
| `llama-server-cuda-sm75.tar.gz` | 684 MB | `bin/llama-server` + the ggml shared libraries (`libllama.so`, `libggml*.so`) preserved at their **build-relative paths** so the binary's `rpath` resolves |
| `cuda-runtime-sm75.tar.gz` | 393 MB | `lib/libcudart.so.12`, `libcublas.so.12`, `libcublasLt.so.12` — the CUDA **runtime** (not the driver) |

Extract both into the same build root:

```
/content/llama.cpp/build/
├── bin/            llama-server, libllama.so, libggml*.so
├── lib/            libcudart.so.12, libcublas.so.12, libcublasLt.so.12
└── ...             ggml libs at their original build-relative paths
```

## Why this exists

Free Colab GPU time arrives in **~10–15 minute bursts** — the compute-unit balance hits
`0.00` and `colab new --gpu T4` starts failing with `Service Unavailable`. But compiling
llama.cpp with CUDA enabled takes **~75–90 minutes** on a Colab T4 (2 vCPUs), because the
`fattn`/`mmq` CUDA template kernels dominate the build.

So on free Colab **a compile can never finish inside one quota allotment**. The VM
idle-recycles mid-build and every bit of progress is lost — which is exactly what happened
repeatedly while setting this up.

**The fix:** compile the engine **once**, publish it here, and let every subsequent VM just
download it. A deploy drops from ~75 minutes of GPU time to **~4 minutes** — small enough to
fit inside a free burst.

### The trick: compile without a GPU

Compiling CUDA code needs `nvcc`, but **not a GPU**. CPU-only Colab sessions are assignable
even when the GPU balance is `0.00`, so the engine was built on a CPU session:

1. CPU-only Colab session (`colab new -s <name>`, no `--gpu`) — assignable at 0.00 GPU balance.
2. Install CUDA 12.6 toolkit via apt (the CPU image ships **no** CUDA toolkit):
   `cuda-nvcc-12-6 cuda-cudart-dev-12-6 libcublas-dev-12-6 cuda-cccl-12-6`
3. `cmake -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=75 -DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=OFF`
4. `cmake --build . --target llama-server -j2` → ~75 min
5. Bundle the binary + ggml libs + CUDA runtime libs, publish.

The CUDA runtime libs are bundled so the binary runs on a GPU VM **regardless of that VM's
CUDA version** (Colab's GPU image ships CUDA 13; the driver is backward compatible with the
bundled CUDA 12 runtime).

## How to use

```bash
# 1. fetch both bundles (anonymous — no token needed)
curl -L -o llama-server-cuda-sm75.tar.gz \
  https://huggingface.co/quangtrang/llama-server-colab-t4/resolve/main/llama-server-cuda-sm75.tar.gz
curl -L -o cuda-runtime-sm75.tar.gz \
  https://huggingface.co/quangtrang/llama-server-colab-t4/resolve/main/cuda-runtime-sm75.tar.gz

# 2. extract into the build root
mkdir -p /content/llama.cpp/build
tar xzf llama-server-cuda-sm75.tar.gz -C /content/llama.cpp/build
tar xzf cuda-runtime-sm75.tar.gz    -C /content/llama.cpp/build

# 3. put the bundled libs on the loader path
export LD_LIBRARY_PATH=/content/llama.cpp/build/bin:/content/llama.cpp/build/lib:$LD_LIBRARY_PATH

# 4. VERIFY — must print a CUDA device
/content/llama.cpp/build/bin/llama-server --list-devices
```

> **Verify with `--list-devices`, not `--version`.** `--version` succeeds even when the CUDA
> libraries can't be loaded, so it will happily pass on a bundle that cannot actually drive a
> GPU. `--list-devices` must print `CUDA` (and the device) or the bundle is broken.

Then serve a model:

```bash
llama-server -m /content/gguf/<model>.gguf \
  --host 0.0.0.0 --port 8000 \
  -ngl 99 -c 49152 \
  --cache-type-k q8_0 --cache-type-v q4_0 \
  -fa on -b 1024 -ub 512 -np 1 --threads 2
```

### Known-good reference configuration

Verified on a Colab T4 with `Qwen3-Coder-30B-A3B-Instruct-UD-IQ3_XXS.gguf`:

| Setting | Value | Why |
|---|---|---|
| `-c` | `49152` | a client's own token accounting can exceed the server's by ~1.3×; 49,152 is the **server** capacity, while the client's declared window is held lower (35,000 for Command Code) so its over-count still fits |
| `--cache-type-k` | `q8_0` | attention keys drive retrieval quality — keep this at 8-bit |
| `--cache-type-v` | `q4_0` | the cheap knob; halves KV memory vs `q8_0` |
| `-fa` | `on` | flash attention (also required for a quantized V cache) |
| `-ub` | `1024` | quantized weights are re-read per ubatch, so a bigger ubatch is much faster prefill |
| `-ngl` | `99` | full GPU offload |

## Using it from any AI client

`llama-server` speaks the **OpenAI API**, so the endpoint works with anything that
accepts a custom base URL — IDE agents, chat UIs, SDKs and CLI tools alike. Command Code
is the client this setup was developed and tested against, but nothing here is specific
to it.

| Setting | Value |
|---|---|
| Base URL | `https://<your-host>/v1` |
| API key | none; the server does not require one |
| Model id | the `--alias` you passed (`qwen3-coder-30b` in the reference config) |

```python
from openai import OpenAI
client = OpenAI(base_url="https://<your-host>/v1", api_key="not-needed")
client.chat.completions.create(model="qwen3-coder-30b", messages=[...])
```

For the full Colab deployment (provisioning, tunnel, keep-alive, and keeping client
configs in sync when the tunnel URL changes) see
[github.com/quangtrang1111/gg-colab-models](https://github.com/quangtrang1111/gg-colab-models).

## Advantages

- **~4 min deploy instead of ~75 min** of GPU time — small enough to fit free Colab bursts.
- **Anonymous download** — the repo is public; no HF token is needed at deploy time.
- **Build once, deploy forever** — the engine never has to be compiled on a quota-limited GPU.
- **Portable across CUDA versions** — the CUDA runtime libs are bundled; only the *driver*
  comes from the host.
- **Reproducible** — same llama.cpp tree, same flags, same CUDA 12.6 toolchain every time.

### Measured on a Colab T4 (IQ3_XXS weights, 49,152 ctx)

| Metric | Value |
|---|---|
| VRAM used | 14,401 MiB of 15,360 MiB (T4) |
| Prefill | 845 tok/s (`-ub 1024`); 613 tok/s at `-ub 256` |
| Decode | ~52 tok/s |
| Deploy time | ~4 min (GGUF download + bundles + load) |

> **VRAM note:** the T4's *effective* ceiling is ~**14.5 GiB**, not the 15,360 MiB
> `nvidia-smi` reports. A 64,576-token context with `q8_0`/`q4_0` KV needs ~14.8 GiB and
> fails with `CUDA error: the resource allocation failed` (raised inside `process_ubatch`,
> not at KV allocation time). For this model (48 layers, 4 KV heads, head_dim 128) the KV
> cost is 49,152 values/token → **52,224 B/token at `q8_0`**, 27,648 B/token at `q4_0`.

## Caveats

- **x86_64 Linux only**, and the GPU must be compute capability **≥ 7.5** (Turing and newer).
  For sm80/sm90 or other architectures, recompile with the matching
  `-DCMAKE_CUDA_ARCHITECTURES`.
- Requires an NVIDIA driver that supports CUDA 12 (driver **525+**). `libcuda.so.1` is the
  driver library and is intentionally **not** bundled — it comes from the host.
- The bundled CUDA runtime is **12.6**; it was produced by extracting the
  `nvidia-cuda-runtime-cu12` / `nvidia-cublas-cu12` Linux wheels.
- Always confirm with `--list-devices` before serving.

## Licenses

- **llama.cpp** and the ggml libraries: MIT (© ggml-org / Georgi Gerganov).
- **CUDA runtime libraries** (`libcudart`, `libcublas`, `libcublasLt`): NVIDIA's CUDA
  Toolkit EULA, redistributable in this form.

## Provenance

Built 2026-11-15 from `ggml-org/llama.cpp` (master, `--depth 1`) on a CPU-only Colab
session with CUDA 12.6, for serving Qwen3-Coder-30B-A3B on a Google Colab T4.
