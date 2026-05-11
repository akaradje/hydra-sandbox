"""LlamaIndex integration tests."""

from __future__ import annotations

import pytest

pytest.importorskip("llama_index", reason="llama-index-core not installed — pip install hydra-pysandbox[llamaindex]")
pytest.importorskip("llama_index.core", reason="llama-index-core not available")
pytest.importorskip("llama_index.core.tools", reason="llama-index-core tools not available")

from hydra_sandbox.integrations.llamaindex import create_safe_python_tool


def test_tool_creation() -> None:
    """create_safe_python_tool must return a FunctionTool."""
    tool = create_safe_python_tool(timeout=10)
    assert tool is not None
    assert hasattr(tool, "fn")
    assert callable(tool.fn)  # type: ignore[attr-defined]


def test_tool_valid_code() -> None:
    """Safe code must execute and return correct output."""
    tool = create_safe_python_tool(timeout=10)
    result = tool("print(2 + 2)")
    assert "4" in result


def test_tool_blocked_import() -> None:
    """Blocked imports must return an error."""
    tool = create_safe_python_tool(timeout=10)
    result = tool("import subprocess")
    assert "Error" in result or "blocked" in result.lower()


def test_tool_timeout() -> None:
    """Infinite loop must be caught."""
    tool = create_safe_python_tool(timeout=2)
    result = tool("while True: pass")
    assert "timeout" in result.lower() or "Error" in result
