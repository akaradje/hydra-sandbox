# hydra-pysandbox

Hardened Python execution sandbox for running untrusted code.

Built for developers building LLM agents, code review bots, and online
coding platforms who need to execute user-submitted or model-generated
Python code without risking the host system.

## Key features

- **Multiple isolation strategies** — subprocess (cross-platform), seccomp
  (Linux syscall filtering), landlock (Linux filesystem sandbox)
- **Import guard** — blocks dangerous stdlib modules
- **Network isolation** — monkey-patches socket creation
- **Resource limits** — CPU, memory, and file descriptor caps (POSIX)
- **Secret purging** — strips API keys from child environment
- **AST signature verification** — structural validation before execution
- **Z3 formal verification** — pre/post-condition mathematical proofs
- **Merkle audit trail** — tamper-evident execution log
- **Escape attempt test suite** — 20+ known bypass vectors tested

## Installation

```bash
pip install hydra-pysandbox

# With optional dependencies
pip install hydra-pysandbox[verify]    # Z3 formal verification
pip install hydra-pysandbox[seccomp]   # Linux seccomp support
pip install hydra-pysandbox[landlock]  # Linux landlock support
pip install hydra-pysandbox[all]       # everything
```

## Quick example

```python
from hydra_sandbox import execute_python

result = execute_python("print(1 + 1)", timeout=5)
print(result.success)  # True
print(result.stdout)   # "2"
```
