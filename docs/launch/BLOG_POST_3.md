# Formally Verifying LLM Output with Z3

LLM-generated code is unreliable. We know this. But what if you could
mathematically prove that a generated function is correct before running
it?

hydra-sandbox integrates Z3, Microsoft's SMT solver, to check
pre-conditions and post-conditions against generated code. Here's how
it works.

## The idea

Formal verification means proving that a function satisfies its
specification for ALL possible inputs. Not testing with a few examples —
proving it mathematically.

For a simple `add` function:

```python
def add(x: int, y: int) -> int:
    return x + y
```

The specification says: for all integers x, y where x ≥ 0 and y ≥ 0,
the result must equal x + y.

In Z3, this becomes a logical formula:

```
∀x,y . (x ≥ 0 ∧ y ≥ 0) → (result = x + y)
```

If this formula is a tautology (always true), the function is correct
for all valid inputs. If there's a counterexample, Z3 tells you exactly
what input would break it.

## Using hydra-sandbox's verified_execute

The combined API makes this dead simple:

```python
from hydra_sandbox import verified_execute

code = "def add(x: int, y: int) -> int:\n    return x + y"

spec = {
    "args": {"x": "Int", "y": "Int"},
    "precondition": "x >= 0 and y >= 0",
    "postcondition": "result == x + y",
}

result = verified_execute(code, "add", spec, timeout=5)

print(result.verification_valid)  # True — mathematically proven
print(result.execution_success)   # True — ran without errors
print(result.z3_proof_hash)       # sha256 for audit trail
```

If the spec had a bug — say `"postcondition": "result > x + y"` — Z3
would find the counterexample and the verification would fail BEFORE
execution. The sandbox never runs code that can't be proven correct.

## A real example: catching a logic error

Let's say an LLM generates a `max` function:

```python
def maximum(a: int, b: int) -> int:
    if a > b:
        return a
    return a  # BUG: should return b
```

The spec says: result ≥ a AND result ≥ b AND (result = a OR result = b).

Z3 finds a counterexample almost instantly: a=2, b=5. The function
returns 2 (a) instead of 5 (b). Verification fails. The code never
touches the sandbox.

This is especially powerful for LLM pipelines where you can't trust the
generated code. Instead of hoping the model got it right, you PROVE it.

## The Z3 integration is optional

The base hydra-sandbox package has zero required dependencies. Z3
verification is an optional extra:

```bash
pip install hydra-sandbox[verify]
```

Without it, verified_execute() still works — it just runs the code
without the proof step. The API is the same.

## Proof hashes as audit trail

Every verification produces a deterministic SHA-256 hash of the code +
spec + result. This means you can:

- Cache verification results (same code+spec → same hash)
- Prove to a third party that code was verified before execution
- Build compliance reports with cryptographic evidence

Combined with the Merkle audit trail, you get end-to-end verifiability:
prove the code was correct → prove the execution was logged → prove the
log hasn't been tampered with.

## When to use it

Formal verification has costs — Z3 can take milliseconds to seconds
depending on constraint complexity. It's not for every function.

Use it for:
- Security-critical code (crypto, auth, input validation)
- Code that will run in production with real data
- Functions with clear input/output contracts

Skip it for:
- I/O-heavy code (network calls, file operations)
- Functions with side effects
- Quick prototypes where test cases suffice

The beauty of the optional integration is that you can start without Z3
and add verification later — no code changes needed.

---

hydra-sandbox is MIT-licensed. pip install hydra-sandbox.
github.com/akaradje/hydra-sandbox
