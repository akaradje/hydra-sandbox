# hydra-pysandbox

[![PyPI](https://img.shields.io/pypi/v/hydra-pysandbox.svg)](https://pypi.org/project/hydra-pysandbox/)
[![Downloads](https://img.shields.io/pypi/dm/hydra-pysandbox.svg)](https://pypi.org/project/hydra-pysandbox/)
[![Python](https://img.shields.io/pypi/pyversions/hydra-pysandbox.svg)](https://pypi.org/project/hydra-pysandbox/)
[![License](https://img.shields.io/pypi/l/hydra-pysandbox.svg)](https://github.com/akaradje/hydra-sandbox/blob/main/LICENSE)
[![Tests](https://img.shields.io/github/actions/workflow/status/akaradje/hydra-pysandbox/test.yml?label=tests)](https://github.com/akaradje/hydra-sandbox/actions)
[![Coverage](https://img.shields.io/codecov/c/github/akaradje/hydra-pysandbox)](https://codecov.io/gh/akaradje/hydra-pysandbox)

Hardened Python execution sandbox for running untrusted code.

Built for developers building LLM agents, code review bots, and online
coding platforms who need to execute user-submitted or model-generated
code without risking the host system.

## 30-second demo

```python
from hydra_sandbox import execute_python

# This is safe — runs in isolated subprocess with import guard,
# resource limits, network blocking, and filesystem sandboxing.
result = execute_python("""
import os, subprocess  # ← these are BLOCKED by the import guard
print("hello")
""", timeout=5)

print(result.success)          # False — blocked imports
print(result.blocked_imports)  # ['os', 'subprocess']

# Safe code works fine:
result = execute_python("print(sum(range(1000)))", timeout=5)
print(result.stdout.strip())   # 499500
```

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
pip install hydra-pysandbox

# With optional dependencies
pip install hydra-pysandbox[verify]       # Z3 formal verification
pip install hydra-pysandbox[seccomp]      # Linux seccomp support
pip install hydra-pysandbox[landlock]     # Linux landlock support
pip install hydra-pysandbox[all]          # everything
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

## Telemetry

hydra-pysandbox includes optional, **opt-in** telemetry. It is **disabled by
default** and sends nothing unless you explicitly enable it.

When enabled, it sends exactly two data points ONCE per process lifetime:
- Package version (`__version__`)
- Strategy selected (`subprocess`, `seccomp`, etc.)

No user code, no environment variables, no PII, no IP address logging.

```bash
export HYDRA_SANDBOX_TELEMETRY=1   # opt in
export HYDRA_SANDBOX_NO_TELEMETRY=1  # explicitly opt out (default)
```

## Acknowledgements

Extracted from [Hydra RSI Core](https://github.com/akaradje/HYDRA_AGI_TECHNICAL),
an experimental multi-agent AGI research framework.

## License

MIT — see [LICENSE](LICENSE) for details.
