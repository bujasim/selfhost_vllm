# RunPod vLLM Guide

This repo now treats the model as runtime config, not source code.

The simplest operating pattern is:

1. Clone the repo once.
2. Keep machine-specific settings in `.env.model`.
3. Start the server with `bash ./serve.sh`.
4. Switch models with `bash ./set_model.sh ...` and `bash ./set_runtime.sh ...`, then restart `serve.sh`.

That removes the old edit / commit / push / pull loop when you want to try a different model.

## 1) Fresh instance bootstrap

Use a Linux pod or VM with:

- 1 GPU
- working NVIDIA drivers
- enough disk under `/workspace`

From the persistent volume:

```bash
cd /workspace
git clone https://github.com/bujasim/selfhost_vllm.git
cd selfhost_vllm
bash ./setup_runpod.sh
```

What that does:

- installs `uv` if needed
- forces Hugging Face cache onto `/workspace` by default
- syncs the Python environment
- creates `.env.model` from `.env.model.example` if it does not exist
- writes `.env.runpod` with cache-related environment exports

## 2) Pick the model

The repo-local model settings live in `.env.model`, but you do not need to edit that file by hand on the pod.

Default file:

```bash
MODEL=Qwen/Qwen3.5-0.8B
HOST=0.0.0.0
PORT=8000
MAX_MODEL_LEN=12288
GPU_MEMORY_UTILIZATION=0.92
MAX_NUM_BATCHED_TOKENS=16384
TENSOR_PARALLEL_SIZE=1
REASONING_PARSER=qwen3
LANGUAGE_MODEL_ONLY=1
TRUST_REMOTE_CODE=0
ENABLE_PREFIX_CACHING=1
```

Fastest way to swap just the model name:

```bash
bash ./set_model.sh Qwen/Qwen3.5-0.8B
```

If the target model needs a parser too:

```bash
bash ./set_model.sh Qwen/Qwen3.5-0.8B qwen3
```

Then open `.env.model` and adjust flags if the new model differs:

- clear `REASONING_PARSER` if the model does not use one
- set `LANGUAGE_MODEL_ONLY=0` if that flag should not be passed
- set `TRUST_REMOTE_CODE=1` only when needed
- tune `MAX_MODEL_LEN` and `GPU_MEMORY_UTILIZATION` per model size

If you do not want to edit files manually, use `set_runtime.sh`:

```bash
bash ./set_runtime.sh TENSOR_PARALLEL_SIZE 2 MAX_MODEL_LEN 8192
```

That updates `.env.model` for you.

## 3) Start the server

```bash
bash ./serve.sh
```

That script reads:

- `.env.runpod` for cache paths
- `.env.model` for model and vLLM flags

and launches `uv run vllm serve ...` with those values.

If you want setup and first launch in one step:

```bash
bash ./setup_runpod.sh --serve
```

## 4) Switch models on an existing instance

If the repo is already cloned and dependencies are already synced:

```bash
cd /workspace/selfhost_vllm
bash ./set_model.sh meta-llama/Llama-3.1-8B-Instruct
bash ./set_runtime.sh TENSOR_PARALLEL_SIZE 2
```

If that model needs different flags, set them with `set_runtime.sh`, then restart the server:

```bash
bash ./serve.sh
```

If the old server is still running in the foreground, stop it first with `Ctrl+C`.

The important point is that switching models is now a config change on the instance, not a code change in git.

## 5) Smoke test

After the server is up:

```bash
uv run smoke_test.py
```

The smoke test now reads the same runtime config, so it targets the configured model automatically.

## 6) Benchmarks

The checked-in benchmark scripts also read `.env.model` automatically:

```bash
uv run bench_unique.py
uv run bench_prefix_cache.py
uv run bench_realistic_sweep.py
```

You can still override values per command with shell env vars when needed:

```bash
MODEL=meta-llama/Llama-3.1-8B-Instruct uv run bench_unique.py
```

Shell env vars override `.env.model` for that command only.

## 7) Fresh 2-GPU pod without editing files

For a brand-new 2-GPU RunPod instance:

```bash
cd /workspace
git clone https://github.com/bujasim/selfhost_vllm.git
cd selfhost_vllm
bash ./setup_runpod.sh
bash ./set_model.sh Qwen/Qwen3.5-397B-A17B-FP8 qwen3
bash ./set_runtime.sh TENSOR_PARALLEL_SIZE 2
bash ./serve.sh
```

If the model still does not fit, lower context length next:

```bash
bash ./set_runtime.sh MAX_MODEL_LEN 8192
bash ./serve.sh
```
