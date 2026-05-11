"""
Sandbox isolation tests — filesystem, network, secrets, imports, limits.

Ported from hydra-rsi-core and expanded for the standalone package.
"""

from __future__ import annotations

import os
import sys
import textwrap

import pytest

from hydra_sandbox import ExecutionResult, execute_python

IS_WINDOWS: bool = sys.platform == "win32"


def run_sandbox(code: str, **kwargs) -> ExecutionResult:
    """Convenience wrapper for execute_python."""
    return execute_python(textwrap.dedent(code), **kwargs)


# ---------------------------------------------------------------------------
# Filesystem isolation
# ---------------------------------------------------------------------------


def test_filesystem_isolation_tempdir() -> None:
    """The sandbox should run in a temporary directory, not the project root."""
    code = """
import os
cwd = os.getcwd()
assert "sandbox" in cwd.lower(), f"Expected temp sandbox dir, got {cwd}"
print("OK: isolated filesystem")
"""
    result = run_sandbox(code, timeout=10)
    assert result.success, f"Filesystem isolation failed: {result.stderr}"
    assert "OK: isolated filesystem" in result.stdout


def test_filesystem_isolation_cannot_list_home() -> None:
    """The sandbox has a temp HOME, not the real user home."""
    code = """
import os
home = os.environ.get("HOME", "")
assert "sandbox" in home.lower() or home == "", f"HOME leaked: {home}"
print("OK: home isolated")
"""
    result = run_sandbox(code, timeout=10)
    assert result.success, f"HOME isolation failed: {result.stderr}"


# ---------------------------------------------------------------------------
# Network blocking
# ---------------------------------------------------------------------------


def test_network_blocked_by_default() -> None:
    """With allow_network=False, socket creation must raise PermissionError."""
    code = """
try:
    import socket
    s = socket.socket()
    raise AssertionError("Network should have been blocked")
except PermissionError:
    print("OK: network blocked")
"""
    result = run_sandbox(code, timeout=10, allow_network=False)
    assert result.success, f"Network blocking test crashed: {result.stderr}"
    assert "OK: network blocked" in result.stdout


def test_network_allowed_when_requested() -> None:
    """With allow_network=True, socket.socket() should not raise."""
    code = """
try:
    import socket
    s = socket.socket()
    print("OK: network allowed")
    s.close()
except PermissionError:
    print("ERROR: network blocked when it should be allowed")
    raise
"""
    result = run_sandbox(code, timeout=10, allow_network=True)
    assert result.success, f"Network allow test failed: {result.stderr}"
    assert "OK: network allowed" in result.stdout


# ---------------------------------------------------------------------------
# Secret purging
# ---------------------------------------------------------------------------


def test_secrets_not_leaked_to_sandbox() -> None:
    """Environment variables containing API keys must not reach the sandbox."""
    os.environ["DEEPSEEK_API_KEY"] = "sk-test-leak-check"
    try:
        code = """
import os
key = os.environ.get("DEEPSEEK_API_KEY", None)
if key is not None:
    raise AssertionError("API key leaked into sandbox!")
print("OK: no leaked secrets")
"""
        result = run_sandbox(code, timeout=10)
        assert result.success, f"Secret leak test failed: {result.stderr}"
        assert "OK: no leaked secrets" in result.stdout
    finally:
        del os.environ["DEEPSEEK_API_KEY"]


# ---------------------------------------------------------------------------
# Import guard — blocked modules
# ---------------------------------------------------------------------------


def test_import_guard_blocks_subprocess() -> None:
    """Importing subprocess inside the sandbox must raise PermissionError."""
    code = """
try:
    import subprocess
    raise AssertionError("subprocess should be blocked")
except PermissionError:
    print("OK: subprocess blocked")
"""
    result = run_sandbox(code, timeout=10)
    assert result.success, f"Import guard test failed: {result.stderr}"
    assert "OK: subprocess blocked" in result.stdout


def test_import_guard_blocks_signal() -> None:
    """signal module should be blocked by import guard."""
    code = """
try:
    import signal
    raise AssertionError("signal should be blocked")
except PermissionError:
    print("OK: signal blocked")
"""
    result = run_sandbox(code, timeout=10)
    assert result.success, f"signal guard test failed: {result.stderr}"
    assert "OK: signal blocked" in result.stdout


def test_import_guard_blocks_ctypes() -> None:
    """ctypes should be blocked."""
    code = """
try:
    import ctypes
    raise AssertionError("ctypes should be blocked")
except PermissionError:
    print("OK: ctypes blocked")
"""
    result = run_sandbox(code, timeout=10)
    assert result.success, f"ctypes block test failed: {result.stderr}"


def test_import_guard_blocks_multiprocessing() -> None:
    """multiprocessing should be blocked."""
    code = """
try:
    import multiprocessing
    raise AssertionError("multiprocessing should be blocked")
except PermissionError:
    print("OK: multiprocessing blocked")
"""
    result = run_sandbox(code, timeout=10)
    assert result.success, f"multiprocessing block test failed: {result.stderr}"


# ---------------------------------------------------------------------------
# Import guard — allowed modules
# ---------------------------------------------------------------------------


def test_import_guard_allows_math() -> None:
    """math module must import cleanly in the sandbox."""
    code = """
import math
print(f"OK: math.sqrt(4)={math.sqrt(4)}")
"""
    result = run_sandbox(code, timeout=10)
    assert result.success, f"math import test failed: {result.stderr}"
    assert "OK:" in result.stdout


def test_import_guard_allows_json() -> None:
    """json module must import cleanly."""
    code = """
import json
data = {"key": "value"}
print(f"OK: {json.dumps(data)}")
"""
    result = run_sandbox(code, timeout=10)
    assert result.success, f"json import test failed: {result.stderr}"
    assert "OK:" in result.stdout


def test_import_guard_allows_hashlib() -> None:
    """hashlib module must import cleanly."""
    code = """
import hashlib
h = hashlib.sha256(b"test").hexdigest()
print(f"OK: sha256={h[:8]}")
"""
    result = run_sandbox(code, timeout=10)
    assert result.success, f"hashlib import test failed: {result.stderr}"
    assert "OK:" in result.stdout


# ---------------------------------------------------------------------------
# Blocked imports tracking
# ---------------------------------------------------------------------------


def test_blocked_imports_tracked_in_result() -> None:
    """ExecutionResult.blocked_imports should list blocked attempts."""
    code = """
try:
    import subprocess
except PermissionError:
    pass
"""
    result = run_sandbox(code, timeout=10, allow_network=False)
    assert result.success, f"Blocked import tracking crashed: {result.stderr}"
    assert isinstance(result.blocked_imports, list)


# ---------------------------------------------------------------------------
# Resource limits — POSIX only
# ---------------------------------------------------------------------------


@pytest.mark.skipif(IS_WINDOWS, reason="POSIX resource limits unavailable on Windows")
def test_memory_limit_enforced_posix() -> None:
    """Attempting a large allocation must fail under RLIMIT_AS on POSIX."""
    code = """
try:
    huge = [0] * (10_000_000_000 // 8)
    print("ERROR: allocation succeeded")
except MemoryError:
    print("OK: MemoryError raised")
"""
    result = run_sandbox(code, timeout=30)
    assert not result.success or "MemoryError" in result.stderr or "MemoryError" in result.stdout, (
        f"Memory limit not enforced: {result.stdout} {result.stderr}"
    )


@pytest.mark.skipif(IS_WINDOWS, reason="POSIX resource limits unavailable on Windows")
def test_cpu_limit_enforced_posix() -> None:
    """CPU time limit must kill an infinite loop on POSIX."""
    code = """
while True:
    pass
"""
    result = run_sandbox(code, timeout=5)
    assert not result.success, f"CPU limit not enforced: {result}"


# ---------------------------------------------------------------------------
# Output truncation
# ---------------------------------------------------------------------------


def test_output_truncation_large_stdout() -> None:
    """Output exceeding 1 MiB must be truncated with marker."""
    code = """
print("A" * 1_200_000)
"""
    result = run_sandbox(code, timeout=15)
    assert "[...TRUNCATED]" in result.stdout or len(result.stdout.encode()) < 1_200_000, (
        f"Output not truncated: {len(result.stdout)} chars"
    )


def test_output_small_stdout_not_truncated() -> None:
    """Small output must not be truncated."""
    code = """
print("hello world")
"""
    result = run_sandbox(code, timeout=5)
    assert result.success
    assert result.stdout.strip() == "hello world"
    assert "[...TRUNCATED]" not in result.stdout


# ---------------------------------------------------------------------------
# Basic execution
# ---------------------------------------------------------------------------


def test_simple_expression() -> None:
    """A simple expression must execute cleanly."""
    result = execute_python("print(1 + 1)", timeout=5)
    assert result.success
    assert "2" in result.stdout


def test_function_definition() -> None:
    """A function definition must execute cleanly."""
    code = """
def add(x, y):
    return x + y
print(add(3, 4))
"""
    result = run_sandbox(code, timeout=5)
    assert result.success
    assert "7" in result.stdout


def test_exception_captured() -> None:
    """Code that raises an exception should report failure."""
    result = execute_python("raise ValueError('test error')", timeout=5)
    assert not result.success
    assert result.exit_code == 1


def test_execution_result_fields() -> None:
    """ExecutionResult must include all expected fields."""
    result = execute_python("print('hello')", timeout=5)
    assert isinstance(result, ExecutionResult)
    assert result.success
    assert isinstance(result.stdout, str)
    assert isinstance(result.stderr, str)
    assert result.cpu_time is None or isinstance(result.cpu_time, float)
    assert result.peak_memory_kb is None or isinstance(result.peak_memory_kb, int)
    assert isinstance(result.blocked_imports, list)


# ---------------------------------------------------------------------------
# Strategy parameter
# ---------------------------------------------------------------------------


def test_explicit_subprocess_strategy() -> None:
    """Explicit strategy='subprocess' must work."""
    result = execute_python("print('ok')", strategy="subprocess", timeout=5)
    assert result.success
    assert "ok" in result.stdout


def test_auto_strategy_works() -> None:
    """Default strategy='auto' must resolve to a working strategy."""
    result = execute_python("print('auto works')", timeout=5)
    assert result.success
    assert "auto works" in result.stdout


def test_invalid_strategy_raises() -> None:
    """Unknown strategy name must raise ValueError."""
    with pytest.raises(ValueError, match="Unknown strategy"):
        execute_python("pass", strategy="nonexistent")
