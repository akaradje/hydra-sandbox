# Threat Model

## What hydra-pysandbox protects against

### 1. Malicious imports
The import guard blocks dangerous stdlib modules (`subprocess`, `ctypes`,
`socket`, `multiprocessing`, `signal`, `shutil`, `ptrace`) at the Python
import hook level. Every `import` and `__import__` call passes through
`find_spec`, which raises `PermissionError` for blocked modules.

**Covered**: `import subprocess`, `__import__('ctypes')`,
`importlib.import_module('os')`, `compile() + exec()` chains.

### 2. Network access
When `allow_network=False` (default), `socket.socket.__init__` is
monkey-patched to raise `PermissionError`. All socket creation paths —
direct construction, `getattr`, factory functions — are blocked.

### 3. Secret leakage
Environment variables matching `*_TOKEN`, `*_KEY`, `*_SECRET`,
`*_PASSWORD`, `*_CREDENTIAL` are stripped before the child process starts.

### 4. Resource exhaustion
On POSIX: CPU time (30s), address space (512 MiB), and open files (64)
limits are applied via `setrlimit`. On all platforms: wall-clock timeout
and output truncation (1 MiB per stream).

### 5. Output overflow
stdout/stderr are capped at 1 MiB. Excess output is truncated with a
`[...TRUNCATED]` marker.

## Known limitations (subprocess strategy)

### os.system / os.popen via attribute access
`os` is pre-loaded in CPython. `import os; os.system(...)` does an
attribute lookup that bypasses `find_spec`. The import guard cannot
intercept this path.

**Mitigation**: Use `seccomp+landlock` on Linux, which kills the
`execve`/`fork`/`clone` syscalls.

### Filesystem access outside sandbox
The subprocess strategy uses `tempfile.TemporaryDirectory` but does not
enforce kernel-level filesystem restrictions. Code can `open()`, `chdir`,
and `listdir` outside the temp directory.

**Mitigation**: Use `landlock` on Linux 5.13+.

### Object traversal (MRO walk)
`().__class__.__base__.__subclasses__()` can enumerate loaded types.
While blocked imports prevent using discovered classes that depend on
blocked modules, the walk itself cannot be prevented without patching
builtins.

**Mitigation**: Use `seccomp` on Linux, which kills any process-spawning
syscall even if a dangerous class is found.

### Process spawning
`os.fork()`, `os.exec*()` are not blocked by the import guard because
`os` is not in the block list.

**Mitigation**: Use `seccomp` on Linux.

## Strategy comparison

| Threat | subprocess | seccomp | landlock | seccomp+landlock |
|--------|-----------|---------|----------|-----------------|
| Blocked imports | Yes | Yes | Yes | Yes |
| Network isolation | Yes | Yes | Yes | Yes |
| Secret purging | Yes | Yes | Yes | Yes |
| Resource limits | Yes (POSIX) | Yes | Yes (POSIX) | Yes |
| os.system via import os | **No** | **Yes** | No | **Yes** |
| Fork/exec syscalls | **No** | **Yes** | No | **Yes** |
| FS access outside sandbox | **No** | No | **Yes** | **Yes** |
| MRO walk | **Partial** | **Yes** | Partial | **Yes** |

## Reporting vulnerabilities

See [SECURITY.md](https://github.com/akaradje/hydra-sandbox/security/advisories).
