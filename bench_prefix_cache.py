import argparse
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

from runtime_config import get_client_host, load_runtime_config

CONFIG = load_runtime_config()
MODEL = CONFIG["MODEL"]
HOST = get_client_host(CONFIG)
PORT = CONFIG["PORT"]
DEFAULT_CONCURRENCY_LEVELS = [1, 2, 4, 8, 12, 16, 24, 32, 48, 64]
DEFAULT_NUM_PROMPTS = 120
EXTRA_BODY = {"chat_template_kwargs": {"enable_thinking": False}}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", default=PORT)
    parser.add_argument("--prefix-len", type=int, default=5000)
    parser.add_argument("--suffix-len", type=int, default=1000)
    parser.add_argument("--output-len", type=int, default=3000)
    parser.add_argument("--num-prefixes", type=int, default=8)
    parser.add_argument("--num-prompts", type=int, default=DEFAULT_NUM_PROMPTS)
    parser.add_argument("--num-warmups", type=int, default=8)
    parser.add_argument(
        "--concurrency",
        type=int,
        nargs="+",
        default=DEFAULT_CONCURRENCY_LEVELS,
        help="Concurrency levels to sweep, e.g. --concurrency 1 2 4 8 16",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(os.environ.get("OUT", f"bench_prefix_{datetime.now():%Y%m%d_%H%M%S}")),
    )
    return parser.parse_args()


def run_case(args: argparse.Namespace, concurrency: int) -> None:
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
        args.host,
        "--port",
        args.port,
        "--model",
        args.model,
        "--dataset-name",
        "prefix_repetition",
        "--prefix-repetition-prefix-len",
        str(args.prefix_len),
        "--prefix-repetition-suffix-len",
        str(args.suffix_len),
        "--prefix-repetition-output-len",
        str(args.output_len),
        "--prefix-repetition-num-prefixes",
        str(args.num_prefixes),
        "--num-prompts",
        str(args.num_prompts),
        "--num-warmups",
        str(args.num_warmups),
        "--ready-check-timeout-sec",
        "120",
        "--max-concurrency",
        str(concurrency),
        "--save-result",
        "--save-detailed",
        "--result-dir",
        str(args.out),
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
    args = parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for concurrency in args.concurrency:
        run_case(args, concurrency)
    print(f"Results saved in {args.out}")


if __name__ == "__main__":
    main()
