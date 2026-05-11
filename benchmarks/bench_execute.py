"""
Benchmark: compare hydra-pysandbox strategies against raw subprocess.

Usage: python benchmarks/bench_execute.py
"""

from __future__ import annotations

import subprocess
import sys
import time

from hydra_sandbox import execute_python

TRIVIAL_CODE = "print(42)"
ITERATIONS = 50  # lower for CI, raise for real benchmarks


def _median(values: list[float]) -> float:
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    if n % 2 == 1:
        return sorted_vals[n // 2]
    return (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2


def _percentile(values: list[float], pct: float) -> float:
    sorted_vals = sorted(values)
    idx = int(len(sorted_vals) * pct / 100)
    return sorted_vals[min(idx, len(sorted_vals) - 1)]


def bench(name: str, fn, iterations: int = ITERATIONS) -> dict:
    """Run *fn* repeatedly and collect timing stats."""
    times: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        fn()
        times.append((time.perf_counter() - start) * 1000)  # ms
    return {
        "name": name,
        "p50": _median(times),
        "p95": _percentile(times, 95),
        "min": min(times),
        "max": max(times),
    }


def main() -> None:
    print(f"Running {ITERATIONS} iterations per strategy on {sys.platform}...")
    results: list[dict] = []

    # Baseline: raw subprocess
    results.append(
        bench(
            "raw subprocess",
            lambda: subprocess.run(
                [sys.executable, "-c", TRIVIAL_CODE], capture_output=True
            ),
        )
    )
    print(f"  {results[-1]['name']:.<30s} p50={results[-1]['p50']:.1f}ms p95={results[-1]['p95']:.1f}ms")

    # hydra-pysandbox subprocess
    results.append(
        bench(
            "hydra subprocess",
            lambda: execute_python(TRIVIAL_CODE, strategy="subprocess"),
        )
    )
    print(f"  {results[-1]['name']:.<30s} p50={results[-1]['p50']:.1f}ms p95={results[-1]['p95']:.1f}ms")

    # hydra-pysandbox auto
    results.append(
        bench(
            "hydra auto",
            lambda: execute_python(TRIVIAL_CODE, strategy="auto"),
        )
    )
    print(f"  {results[-1]['name']:.<30s} p50={results[-1]['p50']:.1f}ms p95={results[-1]['p95']:.1f}ms")

    # Done
    print()
    baseline = results[0]["p50"]
    for r in results:
        overhead = ((r["p50"] - baseline) / baseline) * 100
        print(f"{r['name']:.<30s} p50={r['p50']:.1f}ms  p95={r['p95']:.1f}ms  overhead={overhead:+.0f}%")


if __name__ == "__main__":
    main()
