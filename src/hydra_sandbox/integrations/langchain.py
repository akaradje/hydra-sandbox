"""LangChain integration — drop-in replacement for PythonREPL.

Requires: pip install hydra-pysandbox[langchain]
"""

from __future__ import annotations

from typing import Any

try:
    from langchain_core.tools import BaseTool  # noqa: F401
except ImportError as exc:
    raise ImportError(
        "LangChain integration requires langchain-core. "
        "Install with: pip install hydra-pysandbox[langchain]"
    ) from exc

from hydra_sandbox import execute_python


class SafePythonTool(BaseTool):
    """Safe Python execution tool for LangChain agents.

    Drop-in replacement for ``langchain.tools.PythonREPL`` with
    3-layer isolation, import guard, and resource limits.

    Example::

        from hydra_sandbox.integrations.langchain import SafePythonTool

        tool = SafePythonTool(timeout=10, allow_network=False)
        agent = create_react_agent(llm, [tool])
    """

    name: str = "python_repl"
    description: str = (
        "Execute Python code safely in an isolated sandbox. "
        "Input must be valid Python. "
        "Returns stdout on success or error message on failure."
    )
    timeout: int = 10
    allow_network: bool = False
    strategy: str = "auto"

    def _run(self, code: str, **kwargs: Any) -> str:
        result = execute_python(
            code,
            timeout=self.timeout,
            allow_network=self.allow_network,
            strategy=self.strategy,
        )
        if result.success:
            return result.stdout.strip() or "(no output)"
        if result.timed_out:
            return f"Error: code timed out after {self.timeout}s."
        return f"Error: {result.stderr[:500]}" if result.stderr else "Error: execution failed."

    async def _arun(self, code: str, **kwargs: Any) -> str:
        return self._run(code)
