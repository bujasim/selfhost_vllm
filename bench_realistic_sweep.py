import os
import subprocess
import sys


CONCURRENCY_LEVELS = [1, 2, 4, 8, 12, 16, 24, 32, 48, 64]


def main() -> None:
    for concurrency in CONCURRENCY_LEVELS:
        print(f"=== realistic concurrency {concurrency} ===", flush=True)
        env = os.environ.copy()
        env["CONCURRENCY"] = str(concurrency)
        result = subprocess.run(
            [sys.executable, "bench_realistic.py"],
            env=env,
            text=True,
            capture_output=True,
            check=True,
        )
        print(result.stdout, end="")
        with open(f"realistic_c{concurrency}.out", "w", encoding="utf-8") as handle:
            handle.write(result.stdout)
            if result.stderr:
                handle.write(result.stderr)


if __name__ == "__main__":
    main()
