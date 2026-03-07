import json
import os
import subprocess
from datetime import datetime
from pathlib import Path


MODEL = os.environ.get("MODEL", "Qwen/Qwen3.5-0.8B")
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = os.environ.get("PORT", "8000")

INPUT_LEN = 4000
OUTPUT_LEN = 1000
NUM_WARMUPS = 8
TEMPERATURE = 0.0

CONCURRENCY_LEVELS = [1, 2, 4, 8, 12, 16, 24, 32, 48, 64]

MIN_NUM_PROMPTS = 5
PROMPTS_PER_CONCURRENCY = 5

OUTPUT_DIR = Path(os.environ.get("OUT", f"bench_unique_{datetime.now():%Y%m%d_%H%M%S}"))
EXTRA_BODY = {"chat_template_kwargs": {"enable_thinking": False}}


def effective_num_prompts(concurrency: int) -> int:
    return max(MIN_NUM_PROMPTS, concurrency * PROMPTS_PER_CONCURRENCY)


def run_case(concurrency: int) -> None:
    num_prompts = effective_num_prompts(concurrency)
    print(f"=== concurrency {concurrency} | num_prompts {num_prompts} ===", flush=True)

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
        "random",
        "--input-len",
        str(INPUT_LEN),
        "--output-len",
        str(OUTPUT_LEN),
        "--num-prompts",
        str(num_prompts),
        "--num-warmups",
        str(NUM_WARMUPS),
        "--temperature",
        str(TEMPERATURE),
        "--ready-check-timeout-sec",
        "120",
        "--max-concurrency",
        str(concurrency),
        "--save-result",
        "--save-detailed",
        "--result-dir",
        str(OUTPUT_DIR),
        "--result-filename",
        f"unique_c{concurrency}.json",
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

    print("Planned sweep:")
    for concurrency in CONCURRENCY_LEVELS:
        print(
            f"  concurrency={concurrency:>4}  "
            f"num_prompts={effective_num_prompts(concurrency)}"
        )

    for concurrency in CONCURRENCY_LEVELS:
        run_case(concurrency)

    print(f"Results saved in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()