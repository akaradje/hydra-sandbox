# Benchmarks

All benchmarks run on Windows 11, Python 3.13, Intel Core i7.
Linux numbers typically 20-30% faster due to faster process spawning.

Run with: `python benchmarks/bench_execute.py`

## Cold start comparison (50 iterations)

| Method | p50 | p95 | Overhead vs raw |
|--------|-----|-----|------------------|
| raw `subprocess.run` | 24.3ms | 32.4ms | baseline |
| hydra-pysandbox subprocess | 35.7ms | 78.7ms | +47% |
| hydra-pysandbox auto | 37.6ms | 52.3ms | +55% |

The sandbox adds ~11-13ms overhead over raw `subprocess.run`, primarily
from import guard preamble compilation, environment sanitization, and
output truncation.

## AST pre-flight throughput

From pytest-benchmark (Windows 11, Python 3.13):

| Test | Rate |
|------|------|
| `verify_ast_signature` (valid) | ~40,000/sec |
| `verify_ast_signature` (mismatch) | ~43,000/sec |

AST verification takes ~24 microseconds — faster than any LLM API call.
Use it as a pre-flight gate to skip sandbox invocation for structurally
invalid code.

## Escape attempt success rate

| Strategy | Attacks blocked | Total | Rate |
|----------|-----------------|-------|------|
| subprocess | 17 | 20 | 85% |
| seccomp | 20 | 20 | 100% |
| seccomp+landlock | 20 | 20 | 100% |

The 3 unblocked attacks under subprocess are documented in
`tests/test_escape_attempts.py` as requiring kernel-level protection.

## Proof annotation overhead

- Creating a `ProofAnnotation` + computing hash: <1ms
- Verifying an annotation: ~50µs (SHA-256 + string comparison)

## Test suite

| Count | Status |
|-------|--------|
| 107 | passing |
| 8 | skipped (platform or optional deps) |
| 0 | failing |
