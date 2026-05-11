# Comparison

How hydra-pysandbox compares to alternatives.

## hydra-pysandbox vs alternatives

| Feature | hydra-pysandbox | e2b | Firejail | Naive subprocess |
|---------|:---:|:---:|:---:|:---:|
| Cross-platform | Yes | No (cloud) | Linux only | Yes |
| No external service | Yes | No | Yes | Yes |
| Import guard | Yes | Yes | No | No |
| Network blocking | Yes | Yes | Yes | No |
| Secret purging | Yes | Partial | No | No |
| AST verification | Yes | No | No | No |
| Z3 formal proofs | Yes | No | No | No |
| Seccomp syscall filter | Yes (opt-in) | No | Yes | No |
| Landlock filesystem | Yes (opt-in) | No | No | No |
| Escape test suite | Yes (20+) | No | No | No |
| Audit trail | Yes (Merkle) | No | No | No |
| Zero deps (core) | Yes | No | N/A | Yes |

### vs e2b

[e2b](https://e2b.dev) is a cloud sandbox service. It provides strong
isolation via Firecracker microVMs but requires an internet connection,
API key, and paid plan for production use.

**hydra-pysandbox** runs entirely locally with no external dependencies.
Choose hydra-pysandbox if you need offline execution, zero latency, or
data privacy guarantees. Choose e2b if you need microVM isolation
without managing Linux kernel features yourself.

### vs Firejail

[Firejail](https://github.com/netblue30/firejail) is a Linux SUID
sandbox that uses namespaces, seccomp, and capabilities.

**hydra-pysandbox** wraps the same kernel features (seccomp, landlock)
with a Python-native API, cross-platform fallback, and LLM-tooling
conveniences (AST check, Z3 proof, audit trail). It does not require
SUID or root.

### vs naive subprocess

Running `subprocess.run([sys.executable, "-c", code])` has none of
the protections hydra-pysandbox provides:

- No import blocking (can `import subprocess` and spawn a shell)
- No network isolation
- No secret purging
- No resource limits
- No output truncation

hydra-pysandbox's default `subprocess` strategy adds all of these with
~10-18 ms overhead.

## When to use which strategy

| Use case | Recommended strategy |
|----------|---------------------|
| LLM agent tool (model generates code) | `subprocess` |
| Student code grading | `subprocess` or `seccomp` |
| PR review bot (untrusted contributors) | `seccomp+landlock` |
| Online coding platform (user submissions) | `seccomp+landlock` |
| CI/CD running third-party scripts | `seccomp+landlock` |
| Local development, offline | `subprocess` |
| Research / training runs | `subprocess` |
