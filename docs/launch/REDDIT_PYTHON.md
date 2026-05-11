r/Python: I built a hardened Python sandbox for running LLM-generated code

Hey r/Python — over the past few months I've been extracting the sandbox
module from a larger AGI research project into a standalone package. The
result is hydra-sandbox, and I think it fills a gap in the ecosystem for
people building LLM tools.

The problem: every LLM agent framework (LangChain, LlamaIndex, CrewAI)
needs to execute model-generated Python. Most just use exec() or
subprocess.run() with zero isolation. That's dangerous even with
"trusted" models — hallucinated imports, infinite loops, and accidental
os.system calls happen all the time.

What hydra-sandbox gives you:

```
pip install hydra-sandbox
```

```python
from hydra_sandbox import execute_python

# Safe by default — no network, no subprocess, no ctypes
result = execute_python(llm_output, timeout=5)
print(result.success)  # True/False

# Or with kernel-level protection on Linux
result = execute_python(llm_output, strategy="seccomp+landlock")
```

Key design choices I'd love feedback on:

1. Zero required dependencies for the core package (pure stdlib).
   Optional: [verify] for Z3 proofs, [seccomp] for syscall filtering.

2. Strategy pattern with auto-detection. subprocess → seccomp →
   seccomp+landlock. Graceful fallback on every platform.

3. Import guard that blocks at the find_spec level — catches
   __import__('subprocess'), importlib, compile+exec, and hex-encoded
   payloads. 20 escape attempts tested.

4. AST signature verification: ~24 microseconds, zero LLM cost.
   Runs before execution to catch structural errors.

5. Known limitations documented honestly. os is pre-loaded in CPython,
   so os.system via attribute access requires seccomp. The threat model
   doc spells out exactly what each strategy covers.

The subprocess strategy adds ~10-18ms overhead vs raw subprocess.run.
AST checks are 40,000+ ops/sec.

Would this be useful in your projects? What would make you trust it for
production? I'm particularly interested in feedback on the escape test
suite — what other bypass vectors should I add?

Code: https://github.com/akaradje/hydra-sandbox
Docs: https://akaradje.github.io/hydra-sandbox
