from __future__ import annotations

import os
from pathlib import Path


DEFAULTS = {
    "MODEL": "Qwen/Qwen3.5-0.8B",
    "HOST": "127.0.0.1",
    "PORT": "8000",
    "MAX_MODEL_LEN": "12288",
    "GPU_MEMORY_UTILIZATION": "0.92",
    "MAX_NUM_BATCHED_TOKENS": "16384",
    "TENSOR_PARALLEL_SIZE": "1",
    "REASONING_PARSER": "qwen3",
    "LANGUAGE_MODEL_ONLY": "1",
    "TRUST_REMOTE_CODE": "0",
    "ENABLE_PREFIX_CACHING": "1",
}

CONFIG_PATH = Path(__file__).with_name(".env.model")


def _parse_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values


def load_runtime_config() -> dict[str, str]:
    config = DEFAULTS.copy()
    config.update(_parse_env_file(CONFIG_PATH))
    for key in DEFAULTS:
        if key in os.environ:
            config[key] = os.environ[key]
    return config


def get_client_host(config: dict[str, str]) -> str:
    host = config["HOST"]
    return "127.0.0.1" if host == "0.0.0.0" else host
