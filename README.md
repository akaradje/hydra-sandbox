# hydra-sandbox

Hardened Python execution sandbox for running untrusted code.

Built for developers building LLM agents, code review bots, and online
coding platforms who need to execute user-submitted or model-generated
code without risking the host system.

## Features

- **Multiple isolation strategies** — subprocess (cross-platform), seccomp
  (Linux syscall filtering), landlock (Linux filesystem sandbox)
- **Import guard** — blocks dangerous stdlib modules (`subprocess`, `ctypes`,
  `socket`, `multiprocessing`, etc.)
- **Network isolation** — monkey-patches `socket.socket` to block outbound
  connections
- **Resource limits** — CPU time, memory, and file descriptor caps (POSIX)
- **Secret purging** — strips API keys and tokens from the child environment
- **AST signature verification** — validates function name and parameter lists
  before execution (zero latency, no LLM cost)
- **Z3 formal verification** — optional pre/post-condition checking with
  mathematical proofs

## Installation

```bash
pip install hydra-sandbox

# With optional dependencies
pip install hydra-sandbox[verify]       # Z3 formal verification
pip install hydra-sandbox[seccomp]      # Linux seccomp support
pip install hydra-sandbox[landlock]     # Linux landlock support
pip install hydra-sandbox[all]          # everything
```

## Quick start

```python
from hydra_sandbox import execute_python

# Run untrusted code in an isolated subprocess
result = execute_python(
    "print(1 + 1)",
    timeout=5,
)

print(result.success)    # True
print(result.stdout)     # "2"
print(result.exit_code)  # 0
```

## Strategy selection

```python
# Auto-detect the strongest available strategy (default)
result = execute_python(code, strategy="auto")

# Explicit strategies
result = execute_python(code, strategy="subprocess")      # cross-platform
result = execute_python(code, strategy="seccomp")          # Linux only
result = execute_python(code, strategy="seccomp+landlock") # strongest
```

## AST verification

```python
from hydra_sandbox import verify_ast_signature, extract_expected_signature

# Verify a function signature without executing
error = verify_ast_signature(
    "def add(x, y): return x + y",
    "add",
    ["x", "y"],
)
print(error)  # None — signature is correct

# Extract expected signature from a description
sig = extract_expected_signature(
    "Write function 'process(data: bytes, key: str) -> str'"
)
print(sig)  # ("process", ["data", "key"])
```

## Z3 formal verification

```python
from z3 import Int
from hydra_sandbox.verify import check_spec, VerificationSpec

x, y = Ints("x y")
spec = VerificationSpec(
    precondition=x > 0,
    postcondition=x + y > y,
)
result = check_spec(spec)
print(result.valid)  # True — mathematically proven
```

## Security

See [SECURITY.md](SECURITY.md) for the threat model and supported versions.

The `subprocess` strategy provides Python-level isolation suitable for
most use cases. For production deployments handling truly untrusted code,
use `seccomp+landlock` on a Linux host with additional hardening.

## License

MIT — see [LICENSE](LICENSE) for details.
