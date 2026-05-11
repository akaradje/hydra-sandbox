"""Proof-carrying code tests."""

from __future__ import annotations

import pytest

from hydra_sandbox.proof import (
    ProofAnnotation,
    parse_proof_annotation,
    verify_proof_annotation,
)


def test_proof_hash_deterministic() -> None:
    """Same spec must produce the same proof hash."""
    p1 = ProofAnnotation.create(
        function_name="add",
        precondition="x >= 0",
        postcondition="result == x + y",
        z3_result="VALID",
    )
    p2 = ProofAnnotation.create(
        function_name="add",
        precondition="x >= 0",
        postcondition="result == x + y",
        z3_result="VALID",
    )
    assert p1.proof_hash == p2.proof_hash


def test_different_spec_different_hash() -> None:
    """Different specs must produce different proof hashes."""
    p1 = ProofAnnotation.create(
        function_name="add",
        precondition="x >= 0",
        postcondition="result == x + y",
        z3_result="VALID",
    )
    p2 = ProofAnnotation.create(
        function_name="add",
        precondition="x > 0",
        postcondition="result == x + y",
        z3_result="VALID",
    )
    assert p1.proof_hash != p2.proof_hash


def test_different_function_different_hash() -> None:
    """Different function names must produce different hashes."""
    p1 = ProofAnnotation.create("add", "True", "True", "VALID")
    p2 = ProofAnnotation.create("sub", "True", "True", "VALID")
    assert p1.proof_hash != p2.proof_hash


def test_different_z3_result_different_hash() -> None:
    """VALID vs INVALID must produce different hashes."""
    p1 = ProofAnnotation.create("f", "True", "True", "VALID")
    p2 = ProofAnnotation.create("f", "True", "True", "INVALID")
    assert p1.proof_hash != p2.proof_hash


def test_to_comment_block() -> None:
    """to_comment_block must produce valid Python comment lines."""
    p = ProofAnnotation.create(
        function_name="add",
        precondition="x >= 0",
        postcondition="result == x + y",
        z3_result="VALID",
    )
    block = p.to_comment_block()
    lines = block.split("\n")
    for line in lines:
        assert line.startswith("#"), f"Expected comment, got: {line}"
    assert "hydra-pysandbox" in block
    assert "@function: add" in block
    assert "@proof_hash: sha256:" in block


def test_to_comment_block_with_counterexample() -> None:
    """to_comment_block must include counterexample when present."""
    p = ProofAnnotation(
        function_name="broken",
        precondition="True",
        postcondition="False",
        z3_result="INVALID",
        counterexample={"x": 42},
        proof_hash="sha256:abc123",
        verified_at="2026-05-12T10:00:00Z",
        hydra_version="0.2.0",
    )
    block = p.to_comment_block()
    assert "@counterexample:" in block


def test_parse_roundtrip() -> None:
    """create → to_comment_block → parse must recover original fields."""
    p = ProofAnnotation.create(
        function_name="add",
        precondition="x >= 0",
        postcondition="result == x + y",
        z3_result="VALID",
    )
    block = p.to_comment_block()
    code = block + "\n\ndef add(x, y):\n    return x + y\n"
    parsed = parse_proof_annotation(code)
    assert parsed is not None
    assert parsed.function_name == "add"
    assert parsed.precondition == "x >= 0"
    assert parsed.postcondition == "result == x + y"
    assert parsed.z3_result == "VALID"
    assert parsed.proof_hash == p.proof_hash


def test_verify_annotation_valid() -> None:
    """verify_proof_annotation must return True for intact annotations."""
    p = ProofAnnotation.create(
        function_name="add",
        precondition="x >= 0",
        postcondition="result == x + y",
        z3_result="VALID",
    )
    code = p.to_comment_block() + "\n\ndef add(x, y):\n    return x + y\n"
    assert verify_proof_annotation(code)


def test_verify_annotation_tampered() -> None:
    """verify_proof_annotation must detect tampered annotations."""
    p = ProofAnnotation.create(
        function_name="add",
        precondition="x >= 0",
        postcondition="result == x + y",
        z3_result="VALID",
    )
    block = p.to_comment_block()
    # Tamper: change the postcondition
    tampered = block.replace("result == x + y", "result > x + y")
    code = tampered + "\n\ndef add(x, y):\n    return x + y\n"
    assert not verify_proof_annotation(code)


def test_verify_annotation_no_annotation() -> None:
    """verify_proof_annotation must return False when no annotation found."""
    code = "def add(x, y):\n    return x + y\n"
    assert not verify_proof_annotation(code)


def test_parse_no_annotation() -> None:
    """parse_proof_annotation must return None when no annotation found."""
    code = "print('hello')\n"
    assert parse_proof_annotation(code) is None


def test_annotation_with_counterexample_parsed() -> None:
    """Annotation with counterexample must parse correctly."""
    p = ProofAnnotation(
        function_name="f",
        precondition="True",
        postcondition="False",
        z3_result="INVALID",
        counterexample={"x": 42},
        proof_hash="sha256:abc123",
        verified_at="2026-05-12T00:00:00Z",
        hydra_version="0.2.0",
    )
    block = p.to_comment_block()
    code = block + "\n\ndef f():\n    pass\n"
    parsed = parse_proof_annotation(code)
    assert parsed is not None
    assert parsed.z3_result == "INVALID"


def test_verified_result_has_proof_annotation() -> None:
    """verified_execute with spec must include proof_annotation in result."""
    pytest.importorskip("z3", reason="z3-solver not installed")

    from hydra_sandbox import verified_execute

    code = "def add(x: int, y: int) -> int:\n    return x + y"
    spec = {
        "args": {"x": "Int", "y": "Int"},
        "precondition": "x >= 0",
        "postcondition": "result == x + y",
    }
    result = verified_execute(code, "add", spec, timeout=5)
    assert result.proof_annotation is not None
    assert result.proof_annotation.function_name == "add"
    assert result.proof_annotation.z3_result == "VALID"
    assert result.proof_annotation.proof_hash.startswith("sha256:")
