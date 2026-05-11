# API Reference

## Core execution

### `execute_python()`

```python
def execute_python(
    code: str,
    *,
    timeout: int = 5,
    allow_network: bool = False,
    extra_allowed_imports: tuple[str, ...] | None = None,
    strategy: str = "auto",
) -> ExecutionResult
```

Run Python code in a hardened child process.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `code` | `str` | required | Python source to execute |
| `timeout` | `int` | `5` | Wall-clock timeout in seconds |
| `allow_network` | `bool` | `False` | If True, allow socket creation |
| `extra_allowed_imports` | `tuple[str, ...]` | `None` | Additional modules to allow |
| `strategy` | `str` | `"auto"` | Sandbox strategy |

### `ExecutionResult`

```python
@dataclass
class ExecutionResult:
    success: bool
    stdout: str
    stderr: str
    exit_code: int | None
    timed_out: bool
    exception_info: str | None
    cpu_time: float | None
    peak_memory_kb: int | None
    blocked_imports: list[str]
```

---

## Verified execution

### `verified_execute()`

```python
def verified_execute(
    code: str,
    function_name: str,
    spec: dict[str, Any] | None = None,
    *,
    timeout: int = 5,
    strategy: str = "auto",
    allow_network: bool = False,
) -> VerifiedResult
```

Combine Z3 formal verification with sandbox execution. If a spec is
provided, the proof is checked first; execution is skipped if the
proof fails.

The `spec` dict has the structure:

```python
spec = {
    "args": {"x": "Int", "y": "Int"},
    "precondition": "x >= 0",
    "postcondition": "result == x + y",
}
```

### `VerifiedResult`

```python
@dataclass
class VerifiedResult:
    execution_success: bool
    execution_result: ExecutionResult | None
    verification_valid: bool
    verification_result: VerificationResult | None
    z3_proof_hash: str
    error: str | None
```

---

## AST verification

### `verify_ast_signature()`

```python
def verify_ast_signature(
    code_string: str,
    expected_func: str,
    expected_args: list[str],
) -> str | None
```

Parse *code_string* and verify that *expected_func* is defined at module
level with exactly *expected_args*. Returns `None` on success or a
human-readable error string.

### `extract_expected_signature()`

```python
def extract_expected_signature(
    description: str,
) -> tuple[str, list[str]] | None
```

Best-effort extraction of `(func_name, [arg_names])` from a task
description. Returns `None` if no signature could be parsed.

---

## Z3 verification (optional)

Requires: `pip install hydra-sandbox[verify]`

### `check_spec()`

```python
def check_spec(spec: VerificationSpec) -> VerificationResult
```

### `VerificationSpec`

```python
@dataclass
class VerificationSpec:
    precondition: z3.ExprRef | None
    postcondition: z3.ExprRef | None
    invariants: list[z3.ExprRef]
```

### `VerificationResult`

```python
@dataclass
class VerificationResult:
    valid: bool
    counterexample: str | None
    notes: str
```

---

## Audit trail

### `AuditLog`

```python
class AuditLog:
    def __init__(self, path: str | Path = "audit.jsonl"): ...
    def record(self, operation: str) -> AuditEntry: ...   # context manager
    def verify_chain(self) -> bool: ...
    def export_csv(self, path: str | Path) -> None: ...
    def __len__(self) -> int: ...
```

### `AuditEntry`

```python
class AuditEntry:
    def add(self, key: str, value: Any) -> None: ...
    def to_dict(self) -> dict[str, Any]: ...
```

---

## Import guard

### `build_guarded_preamble()`

```python
def build_guarded_preamble(
    allow: Iterable[str] | None = None,
) -> str
```

Return a Python preamble that blocks dangerous imports.
