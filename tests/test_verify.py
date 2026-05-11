"""
Z3 formal verification tests.

Requires ``hydra-sandbox[verify]``.  Entire file is skipped if z3
is not installed.
"""

from __future__ import annotations

import pytest

pytest.importorskip("z3", reason="z3-solver not installed — pip install hydra-sandbox[verify]")

from z3 import Bool, Int, Ints, IntVal  # noqa: E402

from hydra_sandbox.verify import (  # noqa: E402
    VerificationResult,
    VerificationSpec,
    check_spec,
    trivial_spec,
)


def test_trivial_spec_passes() -> None:
    """trivial_spec() must always pass verification."""
    spec = trivial_spec()
    result = check_spec(spec)
    assert result.valid


def test_valid_arithmetic_spec() -> None:
    """A trivially true arithmetic spec must pass."""
    x, y = Ints("x y")  # noqa: F821
    spec = VerificationSpec(
        precondition=x > 0,
        postcondition=x + y > y,
    )
    result = check_spec(spec)
    assert result.valid


def test_contradiction_spec_fails() -> None:
    """A contradictory spec must fail."""
    x = Int("x")
    spec = VerificationSpec(
        precondition=x > 0,
        postcondition=x < 0,
    )
    result = check_spec(spec)
    assert not result.valid


def test_empty_spec_vacuously_valid() -> None:
    """A spec with no pre/post conditions is vacuously valid."""
    spec = VerificationSpec()
    result = check_spec(spec)
    assert result.valid
    assert "vacuously" in result.notes.lower()


def test_precondition_only_spec() -> None:
    """Spec with only a precondition must be checked."""
    x = Bool("x")
    spec = VerificationSpec(precondition=x)
    result = check_spec(spec)
    assert result.valid
    assert "satisfiable" in result.notes.lower()


def test_postcondition_only_spec() -> None:
    """Spec with only a postcondition must be checked."""
    x = Bool("x")
    spec = VerificationSpec(postcondition=x)
    result = check_spec(spec)
    assert result.valid


def test_with_invariants() -> None:
    """Spec with invariants must include them as background axioms."""
    x = Int("x")
    spec = VerificationSpec(
        precondition=x > 0,
        postcondition=x > -1,
        invariants=[x > -100],
    )
    result = check_spec(spec)
    assert result.valid


def test_verification_result_fields() -> None:
    """VerificationResult must have expected fields."""
    spec = trivial_spec()
    result = check_spec(spec)
    assert isinstance(result, VerificationResult)
    assert isinstance(result.valid, bool)
    # counterexample may be None or a model
    assert isinstance(result.notes, str)


def test_unsat_spec_with_pre_and_post() -> None:
    """A spec where postcondition contradicts precondition must fail."""
    x = Int("x")
    spec = VerificationSpec(
        precondition=x == 5,
        postcondition=x != 5,
    )
    result = check_spec(spec)
    assert not result.valid
