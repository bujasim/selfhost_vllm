#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ -f "${SCRIPT_DIR}/.env.runpod" ]]; then
  # shellcheck disable=SC1091
  source "${SCRIPT_DIR}/.env.runpod"
fi

if [[ -f "${SCRIPT_DIR}/.env.model" ]]; then
  # shellcheck disable=SC1091
  source "${SCRIPT_DIR}/.env.model"
fi

MODEL="${MODEL:-Qwen/Qwen3.5-0.8B}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-12288}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.92}"
MAX_NUM_BATCHED_TOKENS="${MAX_NUM_BATCHED_TOKENS:-16384}"
TENSOR_PARALLEL_SIZE="${TENSOR_PARALLEL_SIZE:-1}"
REASONING_PARSER="${REASONING_PARSER:-qwen3}"
LANGUAGE_MODEL_ONLY="${LANGUAGE_MODEL_ONLY:-1}"
TRUST_REMOTE_CODE="${TRUST_REMOTE_CODE:-0}"
ENABLE_PREFIX_CACHING="${ENABLE_PREFIX_CACHING:-1}"

cmd=(
  uv run vllm serve "$MODEL"
  --host "$HOST"
  --port "$PORT"
  --tensor-parallel-size "$TENSOR_PARALLEL_SIZE"
  --max-model-len "$MAX_MODEL_LEN"
  --gpu-memory-utilization "$GPU_MEMORY_UTILIZATION"
  --max-num-batched-tokens "$MAX_NUM_BATCHED_TOKENS"
)

if [[ -n "$REASONING_PARSER" ]]; then
  cmd+=(--reasoning-parser "$REASONING_PARSER")
fi

if [[ "$LANGUAGE_MODEL_ONLY" == "1" ]]; then
  cmd+=(--language-model-only)
fi

if [[ "$TRUST_REMOTE_CODE" == "1" ]]; then
  cmd+=(--trust-remote-code)
fi

if [[ "$ENABLE_PREFIX_CACHING" == "1" ]]; then
  cmd+=(--enable-prefix-caching)
fi

echo "Serving model: $MODEL"
exec "${cmd[@]}"
