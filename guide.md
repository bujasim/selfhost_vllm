# A40 + vLLM + Qwen3.5-4B Benchmark Guide

This repo is set up to rely on `uv` for Python management.

The key choices are:

- Install `vllm` from the nightly wheel index, because Qwen3.5 currently requires main/nightly vLLM builds.
- Run Qwen in text-only mode with `--language-model-only` so VRAM goes to KV cache instead of the vision path.
- Disable thinking in benchmark requests unless you explicitly want reasoning tokens.
- Keep `--max-model-len` close to the real workload instead of the 262k demo ceiling.

## 1) Prepare the machine

Use a Linux VM or pod with:

- 1x A40
- a working NVIDIA driver
- at least 6 vCPU

Verify the machine first:

```bash
nvidia-smi
uv --version
```

If `nvidia-smi` fails, fix the image before debugging vLLM.

## 2) Put the repo and model cache on persistent storage

If you are on RunPod or any containerized host with a small root filesystem, do not rely on `/` or `/root/.cache`.

The safe pattern is:

- clone the repo under the large mounted volume, usually `/workspace`
- point Hugging Face cache at that same volume

Example:

```bash
cd /workspace
git clone https://github.com/bujasim/selfhost_vllm.git
cd selfhost_vllm

mkdir -p /workspace/hf-cache/hub
export HF_HOME=/workspace/hf-cache
export HUGGINGFACE_HUB_CACHE=/workspace/hf-cache/hub
export UV_LINK_MODE=copy
```

Or use the repo script after cloning:

```bash
cd /workspace/selfhost_vllm
bash ./setup_runpod.sh
```

To bootstrap and immediately launch the server:

```bash
cd /workspace/selfhost_vllm
bash ./setup_runpod.sh --serve
```

Important:

- `cd /workspace` alone does not fix this
- by default, Hugging Face downloads to `~/.cache/huggingface`, which is often on the small root disk
- setting `HF_HOME` and `HUGGINGFACE_HUB_CACHE` is what makes model downloads land on the large volume
- on mounted volumes like `/workspace`, `uv` may not be able to hardlink from its cache into `.venv`; `UV_LINK_MODE=copy` makes that behavior explicit and avoids the warning

You can verify the cache target with:

```bash
echo $HF_HOME
echo $HUGGINGFACE_HUB_CACHE
df -h /workspace
```

## 3) Bootstrap the repo with uv

Clone the repo, then from the repo root run:

```bash
uv python install 3.12
uv sync
```

What this does:

- `uv python install 3.12` ensures the repo uses the pinned Python version from `.python-version`.
- `uv sync` creates `.venv`, installs the dependencies from `pyproject.toml`, and pulls `vllm` from the configured nightly index.
- only `vllm` is pinned to the nightly index; the rest of the dependencies resolve from the default package index

You do not need `python -m venv`, `pip install`, or `source .venv/bin/activate` for the documented workflow.

## 4) Start the server

Run the server through `uv` so the repo-managed environment is always used:

```bash
uv run vllm serve Qwen/Qwen3.5-4B \
  --host 0.0.0.0 \
  --port 8000 \
  --tensor-parallel-size 1 \
  --reasoning-parser qwen3 \
  --language-model-only \
  --max-model-len 12288 \
  --gpu-memory-utilization 0.92 \
  --enable-prefix-caching \
  --max-num-batched-tokens 16384
```

Why this shape:

- `--tensor-parallel-size 1` matches a single GPU deployment.
- `--reasoning-parser qwen3` and `--language-model-only` match Qwen3.5 usage guidance.
- `--max-model-len 12288` fits a practical 6000 in / 3000 out benchmark with some headroom.
- `--gpu-memory-utilization 0.92` is an aggressive starting point on a dedicated host. Drop it if you see OOMs.
- Prefix caching matters for repeated long-prompt workloads.
- `--max-num-batched-tokens 16384` is a useful throughput starting point for a smaller model on a larger GPU.
- Chunked prefill is generally enabled by default in vLLM V1 when supported, so it is not the main tuning lever here.

If you want local API docs:

```bash
uv run vllm serve Qwen/Qwen3.5-4B --enable-offline-docs
```

Keep the `HF_HOME` / `HUGGINGFACE_HUB_CACHE` exports in the same shell before starting the server, or put them in your shell profile for that machine.

## 5) Smoke test the server

Use the checked-in script instead of an inline Python one-liner:

```bash
uv run smoke_test.py
```

That script calls the OpenAI-compatible endpoint on `http://127.0.0.1:8000/v1`, disables thinking, and prints the response plus token usage.

## 6) Run the official unique-prompt benchmark

This is the clean baseline for worst-case-ish non-reused prompts.

```bash
uv run bench_unique.py
```

What it does:

- drives `vllm bench serve`
- sweeps concurrency through `1,2,4,8,12,16,24,32,48,64`
- saves JSON results under a timestamped `bench_unique_*` directory
- waits up to 120 seconds for the endpoint readiness check
- disables thinking in every request

Useful environment overrides:

```bash
MODEL=Qwen/Qwen3.5-4B HOST=127.0.0.1 PORT=8000 uv run bench_unique.py
```

## 7) Run the shared-prefix benchmark

This measures how much prefix caching can help when requests reuse long prompt prefixes.

```bash
uv run bench_prefix_cache.py
```

That script uses the official `prefix_repetition` dataset and saves results under a timestamped `bench_prefix_*` directory.

## 8) Run the realistic structured-output benchmark

This is closer to a SaaS workflow because it includes:

- OpenAI chat templating
- a large fixed shared prefix
- JSON output mode
- thinking disabled
- real client-side concurrency with `asyncio`

It is not a fixed `6000 in / 3000 out` economics benchmark:

- the prompt shape is approximately fixed on input
- `max_tokens=3000` is only an upper bound on output length
- `response_format={"type":"json_object"}` often yields shorter completions than the synthetic 3k-token ceiling

Use the official CLI scripts for fixed-shape economics. Use `bench_realistic.py` for a product-shaped latency and throughput check.

Run the full concurrency sweep with Python instead of a bash loop:

```bash
uv run bench_realistic_sweep.py
```

Run a single concurrency level if you want to inspect one point:

```bash
CONCURRENCY=16 uv run bench_realistic.py
```

Useful environment overrides:

```bash
OPENAI_BASE_URL=http://127.0.0.1:8000/v1 \
OPENAI_API_KEY=EMPTY \
MODEL=Qwen/Qwen3.5-4B \
TOTAL_REQUESTS=120 \
uv run bench_realistic_sweep.py
```

Outputs:

- `bench_realistic.py` writes `realistic_c<N>.json`
- `bench_realistic_sweep.py` also writes `realistic_c<N>.out`

## 9) Optional: let vLLM search the knee automatically

After the manual sweeps are stable, you can try the built-in sweep tooling:

```bash
uv run vllm bench sweep serve_workload --help
```

I would still do the checked-in scripts first because they are easier to reason about and compare.

## 10) Convert throughput to economics

Once you have measured total tok/s per GPU:

```text
cost_per_job = (GPU_price_per_hour / 3600) * (9000 / measured_total_tok_s)
```

For 6000 input / 3000 output jobs:

- at $0.20/hr, you beat $0.0018/job above about 278 total tok/s
- at $0.40/hr, you beat $0.0018/job above about 556 total tok/s

The main question is:

> What is the highest concurrency where p95 latency is still acceptable, and what total tok/s do I get there?

## 11) Recommended test order

1. `uv run bench_unique.py`
2. `uv run bench_prefix_cache.py`
3. `uv run bench_realistic_sweep.py`
4. Repeat 1-3 with and without `--enable-prefix-caching`
5. Repeat with `--max-model-len 10240`, `12288`, and `16384`

If the shared-prefix benchmark is materially better than the unique benchmark, your real app economics may be better than the pessimistic case because prefix caching only speeds up prefilling, not decoding.
