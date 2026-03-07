#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/workspace}"
HF_HOME_DEFAULT="${WORKSPACE_ROOT}/hf-cache"
export HF_HOME="${HF_HOME:-$HF_HOME_DEFAULT}"
export HUGGINGFACE_HUB_CACHE="${HUGGINGFACE_HUB_CACHE:-${HF_HOME}/hub}"
export UV_LINK_MODE="${UV_LINK_MODE:-copy}"

MODEL="${MODEL:-Qwen/Qwen3.5-0.8B}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-12288}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.92}"
MAX_NUM_BATCHED_TOKENS="${MAX_NUM_BATCHED_TOKENS:-16384}"

usage() {
  cat <<'EOF'
Usage: ./setup_runpod.sh [--serve]

Bootstraps this repo on a RunPod-style Linux host by:
- installing uv if needed
- forcing the Hugging Face cache onto /workspace by default
- installing Python 3.12 via uv
- syncing the project environment

Options:
  --serve    Start the vLLM server after setup

Environment overrides:
  WORKSPACE_ROOT
  HF_HOME
  HUGGINGFACE_HUB_CACHE
  UV_LINK_MODE
  MODEL
  HOST
  PORT
  MAX_MODEL_LEN
  GPU_MEMORY_UTILIZATION
  MAX_NUM_BATCHED_TOKENS
EOF
}

SERVE=0
if [[ $# -gt 1 ]]; then
  usage
  exit 2
fi
if [[ $# -eq 1 ]]; then
  case "$1" in
    --serve) SERVE=1 ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage
      exit 2
      ;;
  esac
fi

if [[ ! -f pyproject.toml ]]; then
  echo "error: run this script from the repo root or keep it in the repo root" >&2
  exit 1
fi

if [[ "$OSTYPE" != linux* ]]; then
  echo "error: this script is intended for Linux hosts" >&2
  exit 1
fi

install_uv() {
  if command -v uv >/dev/null 2>&1; then
    return
  fi

  if ! command -v curl >/dev/null 2>&1; then
    echo "error: curl is required to install uv" >&2
    exit 1
  fi

  echo "Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh

  if [[ -x "${HOME}/.local/bin/uv" ]]; then
    export PATH="${HOME}/.local/bin:${PATH}"
  fi

  command -v uv >/dev/null 2>&1 || {
    echo "error: uv install completed but uv is still not on PATH" >&2
    exit 1
  }
}

install_uv

mkdir -p "$HF_HOME" "$HUGGINGFACE_HUB_CACHE"

cat > .env.runpod <<EOF
export HF_HOME="${HF_HOME}"
export HUGGINGFACE_HUB_CACHE="${HUGGINGFACE_HUB_CACHE}"
EOF

echo "Using repo: $SCRIPT_DIR"
echo "Using HF_HOME: $HF_HOME"
echo "Using HUGGINGFACE_HUB_CACHE: $HUGGINGFACE_HUB_CACHE"
echo "Using UV_LINK_MODE: $UV_LINK_MODE"

uv python install 3.12
uv sync

echo
echo "Setup complete."
echo "To reuse the cache settings in a new shell:"
echo "  source ${SCRIPT_DIR}/.env.runpod"

if [[ $SERVE -eq 1 ]]; then
  exec env HF_HOME="$HF_HOME" HUGGINGFACE_HUB_CACHE="$HUGGINGFACE_HUB_CACHE" \
    uv run vllm serve "$MODEL" \
      --host "$HOST" \
      --port "$PORT" \
      --tensor-parallel-size 1 \
      --reasoning-parser qwen3 \
      --language-model-only \
      --max-model-len "$MAX_MODEL_LEN" \
      --gpu-memory-utilization "$GPU_MEMORY_UTILIZATION" \
      --enable-prefix-caching \
      --max-num-batched-tokens "$MAX_NUM_BATCHED_TOKENS"
fi
