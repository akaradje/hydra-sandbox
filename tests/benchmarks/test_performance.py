"""
Performance benchmarks for critical sandbox paths.

Uses pytest-benchmark. Run with::

    pytest tests/benchmarks --benchmark-only
"""

from __future__ import annotations

import subprocess
import sys
import textwrap

import pytest

from hydra_sandbox import execute_python, verify_ast_signature


# ---------------------------------------------------------------------------
# AST verify_ast_signature throughput
# ---------------------------------------------------------------------------


@pytest.mark.benchmark(group="ast", min_rounds=100)
def test_verify_ast_signature_valid(benchmark) -> None:
    """Throughput: verifying a correct function signature."""
    code = "def process(data: bytes, key: str) -> bool:\n    return len(data) > 0\n"

    def _run():
        result = verify_ast_signature(code, "process", ["data", "key"])
        assert result is None

    benchmark(_run)


@pytest.mark.benchmark(group="ast", min_rounds=100)
def test_verify_ast_signature_mismatch(benchmark) -> None:
    """Throughput: detecting a signature mismatch."""
    code = "def process(a, b, c):\n    return a + b + c\n"

    def _run():
        result = verify_ast_signature(code, "process", ["x", "y", "z"])
        assert result is not None

    benchmark(_run)


# ---------------------------------------------------------------------------
# Sandbox execute_python roundtrip
# ---------------------------------------------------------------------------


@pytest.mark.benchmark(group="sandbox", min_rounds=20)
def test_execute_python_trivial(benchmark) -> None:
    """Cold-execute a trivial print statement in the sandbox."""

    def _run():
        result = execute_python("print('hello')", timeout=5, strategy="subprocess")
        assert result.success

    benchmark(_run)


@pytest.mark.benchmark(group="sandbox", min_rounds=20)
def test_execute_python_auto_strategy(benchmark) -> None:
    """Measure auto-detect strategy overhead vs explicit subprocess."""

    def _run():
        result = execute_python("print('ok')", timeout=5, strategy="auto")
        assert result.success

    benchmark(_run)


# ---------------------------------------------------------------------------
# Baseline: raw subprocess.run (no sandbox)
# ---------------------------------------------------------------------------


@pytest.mark.benchmark(group="baseline", min_rounds=50)
def test_raw_subprocess_run(benchmark) -> None:
    """Baseline: raw subprocess.run with no isolation."""

    def _run():
        proc = subprocess.run(
            [sys.executable, "-c", "print('hello')"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert proc.returncode == 0

    benchmark(_run)
