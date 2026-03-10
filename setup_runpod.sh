#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/workspace}"
HF_HOME_DEFAULT="${WORKSPACE_ROOT}/hf-cache"
export HF_HOME="${HF_HOME:-$HF_HOME_DEFAULT}"
export HUGGINGFACE_HUB_CACHE="${HUGGINGFACE_HUB_CACHE:-${HF_HOME}/hub}"
export UV_LINK_MODE="${UV_LINK_MODE:-copy}"

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
  Plus any values in .env.model, or shell env vars that override them
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

if [[ ! -f .env.model ]]; then
  cp .env.model.example .env.model
fi

cat > .env.runpod <<EOF
export HF_HOME="${HF_HOME}"
export HUGGINGFACE_HUB_CACHE="${HUGGINGFACE_HUB_CACHE}"
export UV_LINK_MODE="${UV_LINK_MODE}"
EOF

echo "Using repo: $SCRIPT_DIR"
echo "Using HF_HOME: $HF_HOME"
echo "Using HUGGINGFACE_HUB_CACHE: $HUGGINGFACE_HUB_CACHE"
echo "Using UV_LINK_MODE: $UV_LINK_MODE"
echo "Using model config: ${SCRIPT_DIR}/.env.model"

uv python install 3.12
uv sync

echo
echo "Setup complete."
echo "To reuse the cache settings in a new shell:"
echo "  source ${SCRIPT_DIR}/.env.runpod"
echo "To start the server with the current model config:"
echo "  bash ${SCRIPT_DIR}/serve.sh"

if [[ $SERVE -eq 1 ]]; then
  exec bash "${SCRIPT_DIR}/serve.sh"
fi
