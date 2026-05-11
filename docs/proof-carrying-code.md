# Proof-Carrying Code

hydra-pysandbox v0.2.0 ships with cryptographic proof annotations.
Every function verified via `verified_execute()` gets a signed proof
that can be embedded in source code and audited.

## How it works

1. You provide code + a Z3 specification
2. `verified_execute()` checks the proof
3. If valid, a `ProofAnnotation` is attached to the result
4. The annotation includes a deterministic SHA-256 proof hash

## Usage

```python
from hydra_sandbox import verified_execute

result = verified_execute(
    code="def add(x, y): return x + y",
    function_name="add",
    spec={
        "args": {"x": "Int", "y": "Int"},
        "precondition": "x >= 0 and y >= 0",
        "postcondition": "result == x + y",
    },
)

# Print the proof annotation as a Python comment block
print(result.proof_annotation.to_comment_block())
```

Output:

```python
# Verified by hydra-pysandbox v0.2.0
# @function: add
# @precondition: x >= 0 and y >= 0
# @postcondition: result == x + y
# @z3_result: VALID
# @proof_hash: sha256:a1b2c3d4...
# @verified_at: 2026-05-12T10:23:45Z
```

## Embedding in source

```python
from hydra_sandbox import verified_execute

result = verified_execute(code, "add", spec)
annotated_code = result.proof_annotation.to_comment_block() + "\n\n" + code

with open("verified_add.py", "w") as f:
    f.write(annotated_code)
```

## Verifying annotations

Use the CLI to check an annotated file:

```bash
hydra-sandbox verify-annotation verified_add.py
# Result: VALID — proof annotation is intact.
```

If someone modifies the function or the annotation, verification fails:

```bash
hydra-sandbox verify-annotation tampered_file.py
# Result: TAMPERED — proof hash does not match.
```

## Technical details

- Proof hashes use SHA-256 over the canonical representation
  `function_name|precondition|postcondition|z3_result`
- Hash comparison uses constant-time comparison to prevent timing attacks
- Annotations are valid Python comments — they don't affect execution
- `parse_proof_annotation()` extracts the annotation from any Python file
- `verify_proof_annotation()` recomputes and compares the hash
