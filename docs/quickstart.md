# Quickstart

5-minute guide to executing untrusted Python code safely.

## 1. Install

```bash
pip install hydra-pysandbox
```

## 2. Run untrusted code

```python
from hydra_sandbox import execute_python

code = """
import math
result = math.sqrt(16)
print(f"The answer is {result}")
"""

result = execute_python(code, timeout=5)
print(result.success)   # True
print(result.stdout)    # "The answer is 4.0"
```

## 3. Pick a strategy

```python
# Auto-detect (default)
result = execute_python(code, strategy="auto")

# Force subprocess (cross-platform)
result = execute_python(code, strategy="subprocess")

# Linux-only hardening
result = execute_python(code, strategy="seccomp")
result = execute_python(code, strategy="seccomp+landlock")
```

## 4. Validate before execution

```python
from hydra_sandbox import verify_ast_signature

error = verify_ast_signature(
    "def add(x, y): return x + y",
    "add",
    ["x", "y"],
)
if error is None:
    print("Signature is correct — safe to execute.")
```

## 5. Use with LLM agents

```python
from hydra_sandbox import execute_python

def safe_python_tool(code: str) -> str:
    """LangChain-compatible tool for LLM code execution."""
    result = execute_python(code, timeout=10, strategy="auto")
    return result.stdout if result.success else result.stderr
```

## CLI

```bash
# Run a Python file
hydra-pysandbox run script.py --timeout 10 --strategy auto

# Check function signature
hydra-pysandbox check script.py --expect-function add --expect-args x y

# Show available strategies
hydra-pysandbox doctor

# Run benchmarks
hydra-pysandbox bench
```

## Next steps

- [API Reference](api.md) — complete function documentation
- [Strategies](strategies.md) — when to use which
- [Threat Model](threat-model.md) — what's protected and what's not
