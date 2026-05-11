"""
Example: Z3 formal verification + sandbox execution in one call.

Demonstrates ``verified_execute`` — prove correctness with Z3,
then run in the sandbox with a tamper-evident proof hash.

Requirements: pip install hydra-pysandbox[verify]
"""

from hydra_sandbox import verified_execute


def verify_and_run():
    code = """
def add(x: int, y: int) -> int:
    return x + y
"""

    spec = {
        "args": {"x": "Int", "y": "Int"},
        "precondition": "x >= 0",
        "postcondition": "result == x + y",
    }

    result = verified_execute(code, "add", spec, timeout=5)

    print(f"Verification: {'PASS' if result.verification_valid else 'FAIL'}")
    print(f"Execution:    {'PASS' if result.execution_success else 'FAIL'}")
    print(f"Proof hash:   {result.z3_proof_hash}")
    if result.error:
        print(f"Error:        {result.error}")
    if result.execution_result and result.execution_result.stdout:
        print(f"Output:       {result.execution_result.stdout.strip()}")


def verify_contradiction():
    """A spec that can't possibly hold — verification rejects before execution."""
    code = """
def broken(x: int) -> int:
    return 0
"""

    spec = {
        "args": {"x": "Int"},
        "precondition": "x > 0",
        "postcondition": "False",  # impossible
    }

    result = verified_execute(code, "broken", spec, timeout=5)
    print(f"Verification: {'PASS' if result.verification_valid else 'FAIL'}")
    print(f"Execution:    SKIPPED (verification failed)")
    print(f"Proof hash:   {result.z3_proof_hash}")
    print(f"Reason:       {result.error}")


if __name__ == "__main__":
    print("=== Valid function ===")
    verify_and_run()
    print()
    print("=== Contradictory spec ===")
    verify_contradiction()
