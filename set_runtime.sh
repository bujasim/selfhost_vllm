#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if (( $# == 0 )) || (( $# % 2 != 0 )); then
  echo "Usage: ./set_runtime.sh <KEY> <VALUE> [<KEY> <VALUE> ...]" >&2
  exit 2
fi

CONFIG_PATH="${SCRIPT_DIR}/.env.model"

if [[ ! -f "$CONFIG_PATH" ]]; then
  cp "${SCRIPT_DIR}/.env.model.example" "$CONFIG_PATH"
fi

python3 - "$CONFIG_PATH" "$@" <<'PY'
from pathlib import Path
import sys

config_path = Path(sys.argv[1])
args = sys.argv[2:]

allowed_keys = {
    "MODEL",
    "HOST",
    "PORT",
    "MAX_MODEL_LEN",
    "GPU_MEMORY_UTILIZATION",
    "MAX_NUM_BATCHED_TOKENS",
    "TENSOR_PARALLEL_SIZE",
    "REASONING_PARSER",
    "LANGUAGE_MODEL_ONLY",
    "TRUST_REMOTE_CODE",
    "ENABLE_PREFIX_CACHING",
}

lines = config_path.read_text(encoding="utf-8").splitlines()
values = {}
order = []

for line in lines:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        continue
    key, value = stripped.split("=", 1)
    key = key.strip()
    if key not in values:
        order.append(key)
    values[key] = value.strip()

for i in range(0, len(args), 2):
    key = args[i].strip()
    value = args[i + 1]
    if key not in allowed_keys:
        raise SystemExit(f"Unsupported key: {key}")
    values[key] = value
    if key not in order:
        order.append(key)

output = [
    "# Local model settings for this machine.",
    "# Managed by set_model.sh / set_runtime.sh.",
]
for key in order:
    output.append(f"{key}={values[key]}")

config_path.write_text("\n".join(output) + "\n", encoding="utf-8")
PY

echo "Updated ${CONFIG_PATH}"
for ((i = 1; i <= $#; i += 2)); do
  key="${!i}"
  value_index=$((i + 1))
  value="${!value_index}"
  echo "${key}=${value}"
done
echo "Restart the server with: bash ./serve.sh"
