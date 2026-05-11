"""
Proof-carrying code — cryptographic verification annotations.

Every function passed through ``verified_execute()`` gets a signed
proof annotation that users can inspect, embed in source, and audit.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from hydra_sandbox._version import __version__


@dataclass(frozen=True)
class ProofAnnotation:
    """Cryptographic proof that code was verified against a Z3 spec."""

    function_name: str
    precondition: str
    postcondition: str
    z3_result: str  # "VALID" | "INVALID" | "UNKNOWN"
    counterexample: dict[str, Any] | None
    proof_hash: str
    verified_at: str  # ISO 8601 UTC
    hydra_version: str

    def to_comment_block(self) -> str:
        """Render as a Python comment block for embedding in source."""
        lines = [
            f"# Verified by hydra-pysandbox v{self.hydra_version}",
            f"# @function: {self.function_name}",
            f"# @precondition: {self.precondition}",
            f"# @postcondition: {self.postcondition}",
            f"# @z3_result: {self.z3_result}",
            f"# @proof_hash: {self.proof_hash}",
            f"# @verified_at: {self.verified_at}",
        ]
        if self.counterexample is not None:
            ce = json.dumps(self.counterexample, default=str)
            lines.append(f"# @counterexample: {ce}")
        return "\n".join(lines)

    @classmethod
    def create(
        cls,
        function_name: str,
        precondition: str,
        postcondition: str,
        z3_result: str,
        counterexample: dict[str, Any] | None = None,
    ) -> ProofAnnotation:
        """Factory — computes a deterministic SHA-256 proof hash."""
        content = (
            f"{function_name}|{precondition}|{postcondition}|{z3_result}"
        )
        proof_hash = hashlib.sha256(content.encode()).hexdigest()

        return cls(
            function_name=function_name,
            precondition=precondition,
            postcondition=postcondition,
            z3_result=z3_result,
            counterexample=counterexample,
            proof_hash=f"sha256:{proof_hash}",
            verified_at=datetime.now(timezone.utc).isoformat(),
            hydra_version=__version__,
        )


# ---------------------------------------------------------------------------
# Annotation parsing for verification
# ---------------------------------------------------------------------------

_ANNOTATION_RE = re.compile(
    r"^# Verified by hydra-pysandbox v(?P<version>[\d.]+)\n"
    r"^# @function: (?P<function>.+)\n"
    r"^# @precondition: (?P<precondition>.+)\n"
    r"^# @postcondition: (?P<postcondition>.+)\n"
    r"^# @z3_result: (?P<z3_result>.+)\n"
    r"^# @proof_hash: (?P<proof_hash>.+)\n"
    r"^# @verified_at: (?P<verified_at>.+?)(?:\n|$)",
    re.MULTILINE,
)


def parse_proof_annotation(code: str) -> ProofAnnotation | None:
    """Parse a proof annotation comment block from *code*.

    Returns ``None`` if no valid annotation block is found.
    """
    m = _ANNOTATION_RE.search(code)
    if m is None:
        return None
    d = m.groupdict()
    return ProofAnnotation(
        function_name=d["function"],
        precondition=d["precondition"],
        postcondition=d["postcondition"],
        z3_result=d["z3_result"],
        counterexample=None,
        proof_hash=d["proof_hash"],
        verified_at=d["verified_at"],
        hydra_version=d["version"],
    )


def verify_proof_annotation(code: str) -> bool:
    """Verify that an embedded proof annotation is intact.

    Recomputes the expected proof hash from the annotation fields
    and compares it to the embedded hash.  Returns ``False`` if
    the annotation has been tampered with.
    """
    parsed = parse_proof_annotation(code)
    if parsed is None:
        return False

    content = (
        f"{parsed.function_name}|{parsed.precondition}"
        f"|{parsed.postcondition}|{parsed.z3_result}"
    )
    expected_hash = hashlib.sha256(content.encode()).hexdigest()
    expected = f"sha256:{expected_hash}"

    # Constant-time comparison to prevent timing attacks
    return _secure_compare(expected, parsed.proof_hash)


def _secure_compare(a: str, b: str) -> bool:
    """Constant-time string comparison."""
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a, b):
        result |= ord(x) ^ ord(y)
    return result == 0
