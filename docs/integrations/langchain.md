# LangChain Integration

Drop-in replacement for LangChain's `PythonREPL` with 3-layer sandbox
isolation.

## Install

```bash
pip install hydra-pysandbox[langchain]
```

## Usage

```python
from hydra_sandbox.integrations.langchain import SafePythonTool

# Create the safe tool
tool = SafePythonTool(
    timeout=10,
    allow_network=False,   # default
    strategy="auto",       # picks strongest available
)

# Use with any LangChain agent
from langgraph.prebuilt import create_react_agent
agent = create_react_agent(llm, [tool])
agent.invoke({"messages": [{"role": "user", "content": "Calculate 2+2"}]})
```

## What SafePythonTool protects against

| Threat | Blocked? |
|--------|----------|
| `import subprocess` | Yes (PermissionError) |
| `import ctypes` | Yes |
| `import socket` + `socket()` | Yes (monkey-patched) |
| `os.system('rm -rf /')` | Partial (requires seccomp on Linux) |
| Infinite loops | Yes (timeout) |
| Memory bombs | Yes (rlimits on POSIX) |

## API

### SafePythonTool

```python
class SafePythonTool(BaseTool):
    name: str = "python_repl"
    description: str = "Execute Python code safely..."
    timeout: int = 10
    allow_network: bool = False
    strategy: str = "auto"

    def _run(self, code: str) -> str: ...
    async def _arun(self, code: str) -> str: ...
```

See `examples/langchain_agent.py` for a complete working example.
