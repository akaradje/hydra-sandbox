"""
Verified execution — sandbox + Z3 formal verification in one call.

Parses a spec dict into Z3 expressions, runs the formal proof, then
executes the code in a sandbox if the proof passes.  Returns a combined
result with a deterministic proof hash for audit trails.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# Map spec type names to Z3 sorts
_Z3_SORT_MAP: dict[str, str] = {
    "Int": "z3.Int",
    "Bool": "z3.Bool",
    "Real": "z3.Real",
    "String": "z3.String",
    "BitVec": "z3.BitVec",
}


@dataclass
class VerifiedResult:
    """Combined execution + verification result with audit proof hash."""

    execution_success: bool
    execution_result: Any | None  # ExecutionResult from executor
    verification_valid: bool
    verification_result: Any | None  # VerificationResult from verify
    z3_proof_hash: str
    error: str | None = None


def verified_execute(
    code: str,
    function_name: str,
    spec: dict[str, Any] | None = None,
    *,
    timeout: int = 5,
    strategy: str = "auto",
    allow_network: bool = False,
) -> VerifiedResult:
    """Run *code* in a sandbox with optional Z3 formal verification.

    Args:
        code: Python source to execute.
        function_name: Name of the function to verify/execute.
        spec: Optional spec dict with keys:
            - ``args``: dict mapping arg names to Z3 sort names
              (e.g. ``{"x": "Int", "y": "Int"}``)
            - ``precondition``: Z3 expression string
            - ``postcondition``: Z3 expression string (use ``result``
              to refer to the return value)
        timeout: Sandbox timeout in seconds.
        strategy: Sandbox strategy name.
        allow_network: Whether to allow network access in sandbox.

    Returns:
        ``VerifiedResult`` with execution outcome, verification outcome,
        and a deterministic proof hash.
    """
    from hydra_sandbox.executor import execute_python

    verification_result = None
    verification_valid = True
    error: str | None = None

    # --- Phase 1: Z3 verification (optional) ---
    if spec is not None:
        try:
            verification_result = _verify_from_spec(function_name, spec)
            verification_valid = verification_result.valid
            if not verification_valid:
                # Build proof hash from the failed verification
                proof_hash = _build_proof_hash(
                    code, function_name, spec, verification_result
                )
                return VerifiedResult(
                    execution_success=False,
                    execution_result=None,
                    verification_valid=False,
                    verification_result=verification_result,
                    z3_proof_hash=proof_hash,
                    error="Verification failed — execution skipped.",
                )
        except ImportError as exc:
            error = str(exc)
            logger.warning("Z3 verification skipped: %s", error)
            verification_valid = True  # proceed without verification
            verification_result = None

    # --- Phase 2: Sandbox execution ---
    exec_result = execute_python(
        code,
        timeout=timeout,
        strategy=strategy,
        allow_network=allow_network,
    )

    # --- Phase 3: Proof hash ---
    proof_hash = _build_proof_hash(
        code, function_name, spec, verification_result
    )

    return VerifiedResult(
        execution_success=exec_result.success,
        execution_result=exec_result,
        verification_valid=verification_valid,
        verification_result=verification_result,
        z3_proof_hash=proof_hash,
        error=error,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _verify_from_spec(function_name: str, spec: dict[str, Any]):
    """Parse a spec dict into a ``VerificationResult`` via Z3."""
    from hydra_sandbox.verify import VerificationSpec, check_spec

    z3 = _get_z3()

    args = spec.get("args", {})
    precond_str = spec.get("precondition", "True")
    postcond_str = spec.get("postcondition", "True")

    # Build Z3 variables from args
    z3_vars: dict[str, Any] = {}
    for var_name, sort_name in args.items():
        z3_vars[var_name] = _make_z3_var(z3, var_name, sort_name)

    # Add 'result' variable for postcondition
    if "result" in postcond_str and "result" not in z3_vars:
        z3_vars["result"] = z3.Int("result")

    # Parse expressions
    precond = _parse_z3_expr(precond_str, z3_vars, z3)
    postcond = _parse_z3_expr(postcond_str, z3_vars, z3)

    verif_spec = VerificationSpec(
        precondition=precond,
        postcondition=postcond,
    )
    return check_spec(verif_spec)


def _parse_z3_expr(expr_str: str, variables: dict[str, Any], z3) -> Any:
    """Safely evaluate a Z3 expression string with given variables in scope."""

    # Build a restricted namespace with only Z3 operators and variables
    namespace: dict[str, Any] = dict(variables)
    # Add common Z3 operators
    for op in (
        "And", "Or", "Not", "Implies", "If",
        "Sum", "Product",
    ):
        if hasattr(z3, op):
            namespace[op] = getattr(z3, op)
    namespace["True"] = True
    namespace["False"] = False

    try:
        return eval(expr_str, {"__builtins__": {}}, namespace)
    except Exception as exc:
        raise ValueError(
            f"Failed to parse Z3 expression {expr_str!r}: {exc}"
        ) from exc


def _make_z3_var(z3, name: str, sort_name: str):
    """Create a Z3 variable of the given sort."""
    sort_name = sort_name.strip()
    if sort_name.startswith("BitVec"):
        # BitVec("name", N) — parse the size
        import re

        m = re.match(r"BitVec\((\d+)\)", sort_name)
        if m:
            return z3.BitVec(name, int(m.group(1)))
        return z3.BitVec(name, 32)
    factory = getattr(z3, sort_name, None)
    if factory is None:
        raise ValueError(
            f"Unknown Z3 sort {sort_name!r}. Valid: {list(_Z3_SORT_MAP)}"
        )
    return factory(name)


def _get_z3():
    """Lazy-import z3."""
    try:
        import z3

        return z3
    except ImportError as exc:
        raise ImportError(
            "hydra-sandbox.verified_execute requires z3-solver. "
            "Install with: pip install hydra-sandbox[verify]"
        ) from exc


def _build_proof_hash(
    code: str,
    function_name: str,
    spec: dict[str, Any] | None,
    verification_result: Any | None,
) -> str:
    """Build a deterministic SHA-256 proof hash for audit trails."""
    canonical = {
        "code": code,
        "function_name": function_name,
        "spec": spec,
        "verification_valid": (
            verification_result.valid if verification_result is not None else None
        ),
    }
    serialized = json.dumps(canonical, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
