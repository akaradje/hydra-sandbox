# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Threat Model

hydra-sandbox is designed to protect against:

1. **Malicious code execution** — code that attempts to access the filesystem,
   network, or spawn subprocesses
2. **Resource exhaustion** — CPU, memory, and file descriptor limits
3. **Import-based escapes** — using `__import__`, `importlib`, or `ctypes` to
   bypass restrictions
4. **Information disclosure** — leaking environment variables, secrets, or
   host filesystem paths

## Limitations

- **subprocess strategy** (default, cross-platform): Relies on Python-level
  import guards and socket monkey-patching. Determined attackers may bypass
  via AST manipulation or compiled extensions.
- **seccomp strategy** (Linux only): Kernel-level syscall filtering. Requires
  `libseccomp` and the `pyseccomp` package.
- **landlock strategy** (Linux 5.13+): Filesystem access control at the
  kernel level. Requires the `landlock` Python package.

For production deployments handling truly untrusted code, use the
`seccomp+landlock` strategy on a Linux host with additional hardening
(container, VM, or dedicated machine).

## Reporting a Vulnerability

If you discover a sandbox bypass or security vulnerability, please
open a GitHub Security Advisory at:
https://github.com/akaradje/hydra-sandbox/security/advisories

Do NOT open a public issue for security vulnerabilities.
