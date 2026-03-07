import asyncio
import json
import os
import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from openai import AsyncOpenAI
from transformers import AutoTokenizer


BASE_URL = os.environ.get("OPENAI_BASE_URL", "http://127.0.0.1:8000/v1")
API_KEY = os.environ.get("OPENAI_API_KEY", "EMPTY")
MODEL = os.environ.get("MODEL", "Qwen/Qwen3.5-0.8B")

TARGET_INPUT_TOKENS = 6000
TARGET_OUTPUT_TOKENS = 3000
TOTAL_REQUESTS = int(os.environ.get("TOTAL_REQUESTS", "120"))
CONCURRENCY = int(os.environ.get("CONCURRENCY", "16"))
OUTPUT_DIR = Path(os.environ.get("OUT", "."))

SYSTEM_PREFIX = """
You are an extraction engine for a SaaS workflow.
Return only valid JSON.
Follow the schema exactly.
Do not include markdown.
""".strip()


@dataclass
class Result:
    latency_s: float
    ok: bool
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    error: str | None


tokenizer = AutoTokenizer.from_pretrained(MODEL)
client = AsyncOpenAI(base_url=BASE_URL, api_key=API_KEY)


def exact_token_text(target_tokens: int, seed_text: str) -> str:
    chunk = (seed_text.strip() + "\n") * 4000
    ids = tokenizer.encode(chunk, add_special_tokens=False)[:target_tokens]
    return tokenizer.decode(ids)


shared_prefix = exact_token_text(
    5200,
    "Policy: classify, summarize, and propose actions from the following records.",
)


def make_user_prompt(index: int) -> str:
    suffix = exact_token_text(
        TARGET_INPUT_TOKENS - 5200,
        f"Record batch {index}. Customer event log. Status changes, tool outputs, notes, ids, and structured fields.",
    )
    return shared_prefix + "\n\n" + suffix


PROMPTS = [make_user_prompt(index) for index in range(TOTAL_REQUESTS)]


async def one_request(index: int, sem: asyncio.Semaphore) -> Result:
    async with sem:
        started = time.perf_counter()
        try:
            resp = await client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PREFIX},
                    {"role": "user", "content": PROMPTS[index]},
                ],
                max_tokens=TARGET_OUTPUT_TOKENS,
                temperature=0.0,
                response_format={"type": "json_object"},
                extra_body={"chat_template_kwargs": {"enable_thinking": False}},
            )
            elapsed = time.perf_counter() - started

            usage = getattr(resp, "usage", None)
            prompt_tokens = getattr(usage, "prompt_tokens", None) if usage else None
            completion_tokens = getattr(usage, "completion_tokens", None) if usage else None
            total_tokens = getattr(usage, "total_tokens", None) if usage else None

            return Result(
                latency_s=elapsed,
                ok=True,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                error=None,
            )
        except Exception as exc:
            elapsed = time.perf_counter() - started
            return Result(
                latency_s=elapsed,
                ok=False,
                prompt_tokens=None,
                completion_tokens=None,
                total_tokens=None,
                error=str(exc),
            )


def percentile(values: list[float], ratio: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[int(ratio * (len(ordered) - 1))]


async def main() -> None:
    sem = asyncio.Semaphore(CONCURRENCY)
    started = time.perf_counter()
    results = await asyncio.gather(*(one_request(i, sem) for i in range(TOTAL_REQUESTS)))
    wall = time.perf_counter() - started

    oks = [result for result in results if result.ok]
    latencies = [result.latency_s for result in oks]
    totals = [result.total_tokens for result in oks if result.total_tokens is not None]
    prompts = [result.prompt_tokens for result in oks if result.prompt_tokens is not None]
    completions = [result.completion_tokens for result in oks if result.completion_tokens is not None]

    summary = {
        "model": MODEL,
        "total_requests": TOTAL_REQUESTS,
        "concurrency": CONCURRENCY,
        "successes": len(oks),
        "failures": len(results) - len(oks),
        "wall_time_s": wall,
        "req_per_s": (len(oks) / wall) if wall > 0 else None,
        "p50_latency_s": statistics.median(latencies) if latencies else None,
        "p95_latency_s": percentile(latencies, 0.95),
        "mean_latency_s": statistics.mean(latencies) if latencies else None,
        "prompt_tok_s": (sum(prompts) / wall) if prompts else None,
        "completion_tok_s": (sum(completions) / wall) if completions else None,
        "total_tok_s": (sum(totals) / wall) if totals else None,
    }

    print(json.dumps(summary, indent=2))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"realistic_c{CONCURRENCY}.json"
    output_path.write_text(
        json.dumps(
            {
                "summary": summary,
                "results": [asdict(result) for result in results],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    asyncio.run(main())
