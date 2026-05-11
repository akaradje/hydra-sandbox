# Benchmarks

All benchmarks measured on Windows 11, Python 3.13, Intel Core i7.

Run with: `pytest tests/benchmarks --benchmark-only`

## AST Signature Verification

| Test | Mean | OPS/sec | Target |
|------|------|---------|--------|
| `verify_ast_signature` (valid) | 24.5 μs | 40,837 | >10,000 ✅ |
| `verify_ast_signature` (mismatch) | 23.0 μs | 43,506 | >10,000 ✅ |

The AST verifier runs in **~24 microseconds** — zero latency, zero LLM cost.
At 40,000+ operations per second it can gate every code generation call
without becoming a bottleneck.

## Sandbox Execution Roundtrip

| Test | Mean | Baseline |
|------|------|----------|
| Raw `subprocess.run` | 26.2 ms | — |
| `execute_python` (auto strategy) | 36.3 ms | +39% |
| `execute_python` (subprocess strategy) | 43.9 ms | +68% |

The sandbox adds **10-18 ms** overhead over raw `subprocess.run`, primarily
from the import guard preamble compilation and environment setup. This is
well within acceptable bounds for interactive use cases.

## Strategy Overhead

The `auto` strategy has ~3 ms detection overhead at first call (probing
seccomp/landlock availability), cached for subsequent calls. Explicit
strategy selection (`strategy="subprocess"`) skips the probe entirely.
