"""LlamaIndex integration — safe code execution tool.

Requires: pip install hydra-pysandbox[llamaindex]
"""

from __future__ import annotations

from typing import Any

try:
    from llama_index.core.tools import FunctionTool  # noqa: F401
except ImportError as exc:
    raise ImportError(
        "LlamaIndex integration requires llama-index-core. "
        "Install with: pip install hydra-pysandbox[llamaindex]"
    ) from exc

from hydra_sandbox import execute_python


def create_safe_python_tool(
    timeout: int = 10,
    allow_network: bool = False,
    strategy: str = "auto",
) -> Any:
    """Create a safe Python execution ``FunctionTool`` for LlamaIndex.

    Args:
        timeout: Maximum sandbox execution time in seconds.
        allow_network: If True, allow sandbox code to create sockets.
        strategy: Sandbox strategy (``"auto"``, ``"subprocess"``, etc.).

    Returns:
        A ``llama_index.core.tools.FunctionTool`` instance.

    Example::

        from hydra_sandbox.integrations.llamaindex import create_safe_python_tool

        tool = create_safe_python_tool(timeout=10)
        agent = ReActAgent.from_tools([tool], llm=llm)
    """

    def safe_exec(code: str) -> str:
        """Execute Python code in an isolated sandbox.

        Args:
            code: Python source code to execute.

        Returns:
            stdout on success, or error message on failure.
        """
        result = execute_python(
            code,
            timeout=timeout,
            allow_network=allow_network,
            strategy=strategy,
        )
        if result.success:
            return result.stdout.strip() or "(no output)"
        if result.timed_out:
            return f"Error: code timed out after {timeout}s."
        return f"Error: {result.stderr[:500]}" if result.stderr else "Error: execution failed."

    return FunctionTool.from_defaults(
        fn=safe_exec,
        name="safe_python_exec",
        description="Execute Python code safely in an isolated sandbox. "
        "Sandbox blocks dangerous imports, limits CPU/memory, "
        "and prevents network access.",
    )
