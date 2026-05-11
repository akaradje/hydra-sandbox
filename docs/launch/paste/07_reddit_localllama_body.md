For those running local LLMs and giving them code execution tools, here's a safer alternative to naive subprocess.run():

**hydra-pysandbox** — pure Python, no Docker, no cloud:

    pip install hydra-pysandbox

```python
from hydra_sandbox import execute_python

def python_repl_tool(code: str) -> str:
    """Safe tool for your agent."""
    r = execute_python(code, timeout=10, allow_network=False)
    return r.stdout if r.success else r.stderr
```

**Features:**
- Blocks os.system, subprocess, ctypes, socket imports
- Resource limits (CPU, memory, open files)
- Network isolation
- Filesystem sandboxing
- Cross-platform

**Works with:** LangChain, LlamaIndex, custom agents, any LLM framework.

**Tested against 20 escape techniques** — includes object traversal, hex-encoded imports, compile()+exec().

100% offline-friendly. Good for Ollama/llama.cpp users who don't want their agent's code running unrestricted.

GitHub: https://github.com/akaradje/hydra-sandbox