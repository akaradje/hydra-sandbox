"""
Verified execution tests — sandbox + Z3 combined.
"""

from __future__ import annotations

import hashlib

import pytest

from hydra_sandbox import VerifiedResult, verified_execute

pytest.importorskip("z3", reason="z3-solver not installed — pip install hydra-sandbox[verify]")


def test_valid_spec_and_code_both_pass() -> None:
    """Valid spec + valid code must produce execution_success=True and verification_valid=True."""
    code = "def add(x: int, y: int) -> int:\n    return x + y"
    spec = {
        "args": {"x": "Int", "y": "Int"},
        "precondition": "x >= 0",
        "postcondition": "result == x + y",
    }
    result = verified_execute(code, "add", spec, timeout=5)
    assert isinstance(result, VerifiedResult)
    assert result.verification_valid
    assert result.execution_success


def test_invalid_spec_skips_execution() -> None:
    """When Z3 proof fails, execution must be skipped with execution_success=False."""
    code = "def always_five() -> int:\n    return 5"
    spec = {
        "args": {},
        "precondition": "True",
        "postcondition": "False",  # impossible
    }
    result = verified_execute(code, "always_five", spec, timeout=5)
    assert not result.verification_valid
    assert not result.execution_success
    assert result.execution_result is None
    assert "Verification failed" in (result.error or "")


def test_crashing_code_preserves_verification() -> None:
    """Code that crashes must report execution failure while preserving verification result."""
    code = (
        "def bad(x: int) -> int:\n"
        "    raise ValueError('crash')\n"
        "\n"
        "bad(1)\n"
    )
    spec = {
        "args": {"x": "Int"},
        "precondition": "x > 0",
        "postcondition": "result > 0",
    }
    result = verified_execute(code, "bad", spec, timeout=5)
    # Verification might pass (the spec is logically fine)
    assert result.verification_valid
    # But execution should fail because the function raises at runtime
    assert not result.execution_success
    assert result.execution_result is not None


def test_proof_hash_is_deterministic() -> None:
    """Same code + spec must produce the same proof hash every time."""
    code = "def square(x: int) -> int:\n    return x * x"
    spec = {
        "args": {"x": "Int"},
        "precondition": "True",
        "postcondition": "result == x * x",
    }
    hashes = set()
    for _ in range(3):
        result = verified_execute(code, "square", spec, timeout=5)
        hashes.add(result.z3_proof_hash)
    assert len(hashes) == 1, f"Expected one deterministic hash, got {len(hashes)}"


def test_proof_hash_different_for_different_code() -> None:
    """Different code must produce different proof hashes."""
    code_a = "def add(x: int, y: int) -> int:\n    return x + y"
    code_b = "def sub(x: int, y: int) -> int:\n    return x - y"
    spec = {
        "args": {"x": "Int", "y": "Int"},
        "precondition": "True",
        "postcondition": "True",
    }
    hash_a = verified_execute(code_a, "add", spec, timeout=5).z3_proof_hash
    hash_b = verified_execute(code_b, "sub", spec, timeout=5).z3_proof_hash
    assert hash_a != hash_b


def test_no_spec_still_executes() -> None:
    """When spec is None, code must execute normally without verification."""
    code = "def greet() -> str:\n    return 'hello'\n\nprint(greet())"
    result = verified_execute(code, "greet", spec=None, timeout=5)
    assert result.verification_valid  # defaults to True
    assert result.execution_success
    assert "hello" in result.execution_result.stdout


def test_spec_with_bitvec_args() -> None:
    """BitVec sort must be parseable from the spec dict."""
    code = "def xor_bytes(a: bytes, b: bytes) -> bytes:\n    return bytes(x ^ y for x, y in zip(a, b))"
    spec = {
        "args": {"a": "BitVec(8)", "b": "BitVec(8)"},
        "precondition": "True",
        "postcondition": "True",
    }
    result = verified_execute(code, "xor_bytes", spec, timeout=5)
    assert result.verification_valid
    assert result.execution_success


def test_result_dataclass_fields() -> None:
    """VerifiedResult must have all expected fields."""
    code = "def ident(x):\n    return x"
    spec = {
        "args": {"x": "Int"},
        "precondition": "True",
        "postcondition": "result == x",
    }
    result = verified_execute(code, "ident", spec, timeout=5)
    assert isinstance(result.execution_success, bool)
    assert isinstance(result.verification_valid, bool)
    assert isinstance(result.z3_proof_hash, str)
    assert len(result.z3_proof_hash) == 64  # SHA-256 hex digest
