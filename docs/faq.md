# FAQ

## General

### Is hydra-sandbox safe for production?

The `subprocess` strategy provides Python-level isolation suitable for
LLM agent tools and code review bots. For truly untrusted code (e.g.,
user submissions on a public platform), use `seccomp+landlock` on Linux.
See the [Threat Model](threat-model.md) for a complete breakdown.

### Does it work on Windows?

Yes. The `subprocess` strategy works on Windows, macOS, and Linux.
POSIX resource limits (CPU, memory) are Linux/macOS only; Windows
uses wall-clock timeout. Seccomp and landlock strategies are Linux-only
and fall back gracefully with a clear message.

### What Python versions are supported?

Python 3.10 through 3.13.

## Security

### Can code escape the sandbox?

The import guard blocks all known import-based bypasses (`__import__`,
`compile+exec`, `importlib`, hex encoding). Under `subprocess`, `os`
is intentionally importable (it's a core stdlib module). Use `seccomp`
to block the syscalls that `os.system` and `os.fork` depend on.

### Why doesn't the import guard block `os`?

`os` is a fundamental CPython module. Blocking it would break virtually
all legitimate Python code. Instead, `os.system` and `os.popen` are
blocked as specific submodule names. Kernel-level strategies (seccomp)
provide defense-in-depth for the cases where the import guard can't help.

### How do I verify my deployment?

Run `hydra-sandbox doctor` to see which strategies are available.
Run `pytest tests/test_escape_attempts.py -v` to validate that
known bypass vectors are blocked for your configuration.

## Usage

### Can I allow additional imports?

Yes. Pass `extra_allowed_imports=("numpy", "pandas")` to allow libraries
beyond the safe stdlib defaults. The import guard adds them to the
allowlist.

### Can I allow network access?

Yes. Set `allow_network=True` in `execute_python()`. The socket
monkey-patch is skipped.

### How do I set up the audit trail?

```python
from hydra_sandbox import AuditLog, execute_python

audit = AuditLog("execution_audit.jsonl")
with audit.record("user_code_execution") as entry:
    result = execute_python(code)
    entry.add("success", result.success)
    entry.add("exit_code", result.exit_code)

# Verify chain integrity
assert audit.verify_chain()
```

### Can I use it with async code?

The sandbox runs in a subprocess, so it's inherently non-blocking for
the parent process. Wrap in `asyncio.to_thread()` or use a
`ThreadPoolExecutor` if calling from async code.

```python
import asyncio
from hydra_sandbox import execute_python

async def main():
    result = await asyncio.to_thread(execute_python, "print('hello')")
    print(result.success)

asyncio.run(main())
```

## Performance

### What's the overhead?

- AST verification: ~24 µs (40,000+ ops/sec)
- Sandbox startup (subprocess): ~36 ms (+39% vs raw subprocess)
- Sandbox startup (seccomp): ~40-50 ms
- Output truncation: negligible

See [Benchmarks](benchmarks.md) for detailed numbers.

### Can I reduce the overhead?

Use `verify_ast_signature()` before `execute_python()` — a 24 µs pre-check
can skip an entire ~36 ms subprocess invocation for structurally invalid
code.

### Does it slow down over time?

No. The sandbox creates a fresh temp directory and subprocess for each
call. There is no persistent state or memory leak. The temp directory
is cleaned up automatically.
