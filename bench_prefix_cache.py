import json
import os
import subprocess
from datetime import datetime
from pathlib import Path


MODEL = os.environ.get("MODEL", "Qwen/Qwen3.5-0.8B")
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = os.environ.get("PORT", "8000")
CONCURRENCY_LEVELS = [1, 2, 4, 8, 12, 16, 24, 32, 48, 64]
OUTPUT_DIR = Path(os.environ.get("OUT", f"bench_prefix_{datetime.now():%Y%m%d_%H%M%S}"))
EXTRA_BODY = {"chat_template_kwargs": {"enable_thinking": False}}


def run_case(concurrency: int) -> None:
    print(f"=== concurrency {concurrency} ===", flush=True)
    cmd = [
        "vllm",
        "bench",
        "serve",
        "--backend",
        "openai-chat",
        "--endpoint",
        "/v1/chat/completions",
        "--host",
        HOST,
        "--port",
        PORT,
        "--model",
        MODEL,
        "--dataset-name",
        "prefix_repetition",
        "--prefix-repetition-prefix-len",
        "5000",
        "--prefix-repetition-suffix-len",
        "1000",
        "--prefix-repetition-output-len",
        "3000",
        "--prefix-repetition-num-prefixes",
        "8",
        "--num-prompts",
        "120",
        "--num-warmups",
        "8",
        "--ready-check-timeout-sec",
        "120",
        "--max-concurrency",
        str(concurrency),
        "--save-result",
        "--save-detailed",
        "--result-dir",
        str(OUTPUT_DIR),
        "--result-filename",
        f"prefix_c{concurrency}.json",
        "--percentile-metrics",
        "ttft,tpot,e2el",
        "--metric-percentiles",
        "50,95,99",
        "--extra-body",
        json.dumps(EXTRA_BODY, separators=(",", ":")),
    ]
    subprocess.run(cmd, check=True)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for concurrency in CONCURRENCY_LEVELS:
        run_case(concurrency)
    print(f"Results saved in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
