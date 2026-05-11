LangChain's PythonREPL is great for demos but has no isolation. Here's a drop-in-ish replacement:

```python
from hydra_sandbox import execute_python
from langchain.tools import Tool

def safe_python_repl(code: str) -> str:
    r = execute_python(code, timeout=10)
    return r.stdout if r.success else r.stderr

python_tool = Tool(
    name="python_repl",
    func=safe_python_repl,
    description="Safe Python execution with sandbox.",
)
```

**What's different:**
- Blocks dangerous imports (subprocess, ctypes, socket...)
- CPU/memory limits
- Network isolation
- Optional Z3 verification for generated code

Install:

    pip install hydra-pysandbox

GitHub: https://github.com/akaradje/hydra-sandbox

Would love feedback from LangChain users — does the API fit your workflow?