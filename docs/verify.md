# Z3 Formal Verification

hydra-pysandbox can mathematically prove properties of generated code
using Z3, an SMT solver from Microsoft Research.

## Concepts

A **specification** has three parts:

- **Pre-condition**: what must be true BEFORE the function runs
- **Post-condition**: what must be true AFTER the function runs
- **Invariants**: properties that always hold (optional)

Z3 checks whether `precondition ⇒ postcondition` is a logical tautology.
If it is, the post-condition is guaranteed for any input satisfying the
pre-condition.

## Basic usage

```python
from z3 import Int
from hydra_sandbox.verify import check_spec, VerificationSpec

x, y = Ints("x y")

spec = VerificationSpec(
    precondition=x > 0,
    postcondition=x + y > y,
)

result = check_spec(spec)
print(result.valid)   # True — mathematically proven
print(result.notes)   # "Pre ⇒ Post is satisfiable."
```

## Using verified_execute()

The combined API parses a spec dict and handles everything:

```python
from hydra_sandbox import verified_execute

code = """
def add(x: int, y: int) -> int:
    return x + y
"""

spec = {
    "args": {"x": "Int", "y": "Int"},
    "precondition": "x >= 0 and y >= 0",
    "postcondition": "result >= 0",     # sum of non-negatives is non-negative
}

result = verified_execute(code, "add", spec, timeout=5)
# Verification:   PASS
# Execution:      PASS
# Proof hash:     <sha256>
```

## Supported Z3 sorts

The spec dict supports these sort names in the `args` field:

| Sort name | Z3 sort | Example |
|-----------|---------|---------|
| `Int` | `z3.Int` | `"x": "Int"` |
| `Bool` | `z3.Bool` | `"flag": "Bool"` |
| `Real` | `z3.Real` | `"ratio": "Real"` |
| `String` | `z3.String` | `"name": "String"` |
| `BitVec(N)` | `z3.BitVec` | `"hash": "BitVec(256)"` |

## Writing expressions

Pre- and post-conditions are Z3 formula strings. Use the variable names
declared in `args` plus `result` for the return value:

```python
spec = {
    "args": {"a": "Int", "b": "Int"},
    "precondition": "a > 0 and b > 0",
    "postcondition": "result > a and result > b",  # result is max
}
```

## Installation

```bash
pip install hydra-pysandbox[verify]
```

Without `[verify]`, calling `check_spec()` or `verified_execute()` with
a spec raises `ImportError` with a clear installation instruction.
