#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: ./set_model.sh <model> [reasoning_parser]" >&2
  exit 2
fi

MODEL="$1"
REASONING_PARSER="${2-}"
CONFIG_PATH="${SCRIPT_DIR}/.env.model"

if [[ ! -f "$CONFIG_PATH" ]]; then
  cp "${SCRIPT_DIR}/.env.model.example" "$CONFIG_PATH"
fi

python3 - "$CONFIG_PATH" "$MODEL" "$REASONING_PARSER" <<'PY'
from pathlib import Path
import sys

config_path = Path(sys.argv[1])
model = sys.argv[2]
reasoning_parser = sys.argv[3]

lines = config_path.read_text(encoding="utf-8").splitlines()
values = {}
order = []

for line in lines:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        continue
    key, value = stripped.split("=", 1)
    key = key.strip()
    values[key] = value.strip()
    order.append(key)

values["MODEL"] = model
if reasoning_parser:
    values["REASONING_PARSER"] = reasoning_parser

for key in ["MODEL", "HOST", "PORT", "MAX_MODEL_LEN", "GPU_MEMORY_UTILIZATION", "MAX_NUM_BATCHED_TOKENS", "TENSOR_PARALLEL_SIZE", "REASONING_PARSER", "LANGUAGE_MODEL_ONLY", "TRUST_REMOTE_CODE", "ENABLE_PREFIX_CACHING"]:
    if key not in order and key in values:
        order.append(key)

output = [
    "# Local model settings for this machine.",
    "# Change MODEL and any flags that differ for the target model.",
]
for key in order:
    output.append(f"{key}={values[key]}")

config_path.write_text("\n".join(output) + "\n", encoding="utf-8")
PY

echo "Updated ${CONFIG_PATH}"
echo "MODEL=${MODEL}"
if [[ -n "$REASONING_PARSER" ]]; then
  echo "REASONING_PARSER=${REASONING_PARSER}"
fi
echo "Restart the server with: bash ./serve.sh"
