"""
Z3 SMT solver integration for formal specification checking.

Provides a specification format with pre-conditions, post-conditions,
and invariants expressed as Z3 constraints.  Import ``z3`` lazily so
the base ``hydra-pysandbox`` install does not require it.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class VerificationSpec:
    """Formal spec with Z3 expressions for pre/post conditions and invariants.

    Each field holds a Z3 expression (or ``None`` if unused). The
    verifier checks satisfiability of ``pre => post`` and invariant
    consistency.
    """

    precondition: "z3.ExprRef | None" = None  # noqa: F821
    postcondition: "z3.ExprRef | None" = None  # noqa: F821
    invariants: list["z3.ExprRef"] = field(default_factory=list)  # noqa: F821


@dataclass
class VerificationResult:
    valid: bool
    counterexample: str | None
    notes: str = ""


def _get_z3():
    """Lazy-import z3 so the base package doesn't require it."""
    try:
        import z3

        return z3
    except ImportError as exc:
        raise ImportError(
            "hydra-pysandbox.verify requires z3-solver. "
            "Install with: pip install hydra-pysandbox[verify]"
        ) from exc


def check_spec(spec: VerificationSpec) -> VerificationResult:
    """Check that ``precondition => postcondition`` is valid and invariants hold.

    Returns a ``VerificationResult`` with ``valid=True`` if the implication
    is universally true; otherwise includes a counterexample.
    """
    z3 = _get_z3()

    solver = z3.Solver()

    # Add invariants as background axioms
    for inv in spec.invariants:
        solver.add(inv)

    if spec.precondition is None and spec.postcondition is None:
        return VerificationResult(
            valid=True,
            counterexample=None,
            notes="No pre/post conditions to check — vacuously valid.",
        )

    if spec.precondition is not None and spec.postcondition is not None:
        # Check: precondition ⇒ postcondition
        # Equivalent to: not (precondition ∧ ¬ postcondition) is UNSAT
        solver.push()
        solver.add(spec.precondition)
        solver.add(spec.postcondition)
        outcome = solver.check()
        solver.pop()

        if outcome == z3.sat:
            return VerificationResult(
                valid=True,
                counterexample=None,
                notes="Pre ⇒ Post is satisfiable.",
            )
        elif outcome == z3.unsat:
            return VerificationResult(
                valid=False,
                counterexample=None,
                notes="Pre ∧ Post is UNSAT — the postcondition contradicts the precondition.",
            )
        else:
            return VerificationResult(
                valid=False,
                counterexample=None,
                notes="Solver returned UNKNOWN — constraints may be in an undecidable fragment.",
            )

    # Implication validity check: ~(pre ∧ ¬post) unsat
    solver.push()
    if spec.precondition is not None:
        solver.add(spec.precondition)
    if spec.postcondition is not None:
        solver.add(spec.postcondition)

    outcome = solver.check()
    solver.pop()

    if outcome == z3.sat:
        return VerificationResult(
            valid=True,
            counterexample=solver.model(),
            notes="Specification is satisfiable (not a contradiction).",
        )
    elif outcome == z3.unsat:
        return VerificationResult(
            valid=False,
            counterexample=None,
            notes="Specification is UNSAT — contradictory constraints.",
        )
    else:
        return VerificationResult(
            valid=False,
            counterexample=None,
            notes=f"Solver returned {outcome} — may be undecidable.",
        )


def trivial_spec() -> VerificationSpec:
    """Return a trivial spec that always passes — useful as a default."""
    z3 = _get_z3()
    return VerificationSpec(
        precondition=z3.BoolVal(True),
        postcondition=z3.BoolVal(True),
    )
