r/LangChain: Safe Python code execution for your agents

I built hydra-pysandbox after getting frustrated with how most LangChain
tools handle Python execution. The default PythonREPL tool in LangChain
uses exec() in the same process. If the model generates `import os;
os.system('rm -rf /')`, that runs directly on your host.

hydra-pysandbox gives you a drop-in replacement that actually isolates
the code:

```python
from hydra_sandbox import execute_python

def safe_python_repl(code: str) -> str:
    """LangChain-compatible Python tool with real isolation."""
    result = execute_python(code, timeout=10, strategy="auto")
    if result.timed_out:
        return "Error: code timed out."
    if not result.success:
        return f"Error (exit {result.exit_code}): {result.stderr}"
    return result.stdout or "(no output)"
```

Or as a LangChain @tool:

```python
from langchain.tools import tool

@tool
def python_sandbox(code: str) -> str:
    """Execute Python code in a hardened sandbox."""
    result = execute_python(code, timeout=10, strategy="auto")
    if not result.success:
        return f"Error: {result.stderr}"
    return result.stdout
```

What you get vs the default PythonREPL:

- No import of subprocess/ctypes/socket/shutil (import guard blocks
  find_spec)
- No network access (socket monkey-patched)
- No leaked API keys (env sanitized before subprocess)
- No infinite loops taking down your agent (wall-clock timeout)
- No output flooding your context window (>1MB truncated)
- Optional Z3 formal verification if you install [verify]

The subprocess strategy works on Linux, macOS, and Windows. If you're
on Linux, add `strategy="seccomp+landlock"` for kernel-level protection.

I'm looking for early adopters who build LLM tools and care about
security. What would make this a no-brainer for your LangChain projects?

Examples: ./examples/ directory has working LangChain integration sketch
plus PR reviewer bot and student grader examples.

PyPI: https://pypi.org/project/hydra-pysandbox/
GitHub: https://github.com/akaradje/hydra-sandbox
