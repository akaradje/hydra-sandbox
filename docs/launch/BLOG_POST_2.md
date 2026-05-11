# I Built a Sandbox That Runs Untrusted Python (and Tried to Break It)

Over the past few months, I extracted a sandbox module from a larger
research project and turned it into a standalone PyPI package:
hydra-sandbox.

The goal: make running untrusted Python code as safe as possible without
requiring Docker, a cloud VM, or a PhD in Linux security.

## The architecture

The core idea is simple: run user code in a child `python -c` process
with layers of defense:

```
User code
  ↓
Import guard (blocks subprocess, ctypes, socket, etc.)
  ↓
Network block (socket.__init__ → PermissionError)
  ↓
Environment scrub (purge API keys)
  ↓
POSIX resource limits (CPU, memory, files)
  ↓
Output truncation (1 MiB cap)
  ↓
Child process → result returned to parent
```

Each layer catches what the layer above misses. Defense in depth.

## Trying to break it

The most interesting part was building the escape test suite — 20
attacks I tried that the sandbox must block:

**Blocked**:
- `__import__('subprocess')` → PermissionError
- `importlib.import_module('ctypes')` → PermissionError
- `exec(compile('import shutil', '', 'exec'))` → PermissionError
- `exec(bytes.fromhex('696d706f7274206f73').decode())` → PermissionError
- `sys.modules.clear(); import subprocess` → PermissionError
- Socket creation via direct, getattr, and factory paths → PermissionError

**Contained**:
- Infinite recursion → RecursionError (child dies, parent unaffected)
- 500M-element list allocation → MemoryError

**Documented limitations**:
- `import os; os.system('ls')` — os is pre-loaded in CPython, so
  attribute access on os bypasses the import hook. Requires seccomp.
- `().__class__.__base__.__subclasses__()` — MRO walk can enumerate
  types. Requires seccomp to actually prevent process spawning.
- Filesystem access outside tempdir — requires landlock.

## The honest threat model

I didn't want to claim "unbreakable." That's how security tools get a
bad reputation. Instead, I documented exactly what each strategy protects
against and what it doesn't:

| Threat | subprocess | seccomp | seccomp+landlock |
|--------|:---:|:---:|:---:|
| Blocked imports | Yes | Yes | Yes |
| Network isolation | Yes | Yes | Yes |
| os.system via import os | No | Yes | Yes |
| Fork/exec syscalls | No | Yes | Yes |
| FS outside sandbox | No | No | Yes |

For LLM agent tools where the "attacker" is a hallucinating model (not
an adversary), the subprocess strategy is enough. For running truly
untrusted user submissions, you need seccomp+landlock on Linux.

## What surprised me

- The import guard catches way more than I expected. `compile()` +
  `exec()` chains, hex-encoded payloads, `sys.modules` poisoning — all
  hit the same `find_spec` path. The Python import system is well-designed
  for this kind of hook.

- `os` being pre-loaded in CPython is the biggest gap in the subprocess
  strategy. I can't block `os` without breaking essentially all Python
  code. The solution is kernel-level protection (seccomp), not
  Python-level tricks.

- The performance cost is negligible. AST verification at 40,000 ops/sec
  means you can pre-check every LLM output for free. The subprocess
  round-trip at ~36ms is faster than the LLM API call that generated
  the code.

## What's next

I'd love to hear from people building LLM tools: what would make you
trust a sandbox for production? What features am I missing?

The repo is at github.com/akaradje/hydra-sandbox. MIT license.
pip install hydra-sandbox.
