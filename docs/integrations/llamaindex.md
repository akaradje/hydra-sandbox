# LlamaIndex Integration

Safe Python execution as a `FunctionTool` for LlamaIndex agents.

## Install

```bash
pip install hydra-pysandbox[llamaindex]
```

## Usage

```python
from hydra_sandbox.integrations.llamaindex import create_safe_python_tool

# Create the safe tool
tool = create_safe_python_tool(
    timeout=10,
    allow_network=False,
    strategy="auto",
)

# Use with any LlamaIndex agent
from llama_index.core.agent import ReActAgent
agent = ReActAgent.from_tools([tool], llm=llm)
agent.chat("What is 2 + 2? Use Python to calculate it.")
```

## API

### create_safe_python_tool()

```python
def create_safe_python_tool(
    timeout: int = 10,
    allow_network: bool = False,
    strategy: str = "auto",
) -> FunctionTool
```

Returns a `llama_index.core.tools.FunctionTool` configured for safe
Python execution with import guard, resource limits, and network
blocking.

See `examples/llamaindex_tool.py` for a complete working example.
