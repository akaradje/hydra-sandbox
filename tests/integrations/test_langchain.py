"""LangChain integration tests."""

from __future__ import annotations

import sys

import pytest

pytest.importorskip("langchain_core", reason="langchain-core not installed — pip install hydra-pysandbox[langchain]")
pytest.importorskip("langchain_core.tools", reason="langchain-core tools not available")

from hydra_sandbox.integrations.langchain import SafePythonTool


def test_tool_creation() -> None:
    """SafePythonTool must instantiate without error."""
    tool = SafePythonTool(timeout=10)
    assert tool.name == "python_repl"
    assert tool.timeout == 10
    assert not tool.allow_network


def test_tool_valid_code() -> None:
    """Safe code must execute and return correct output."""
    tool = SafePythonTool(timeout=10)
    result = tool._run("print(42)")
    assert "42" in result


def test_tool_blocked_import() -> None:
    """Blocked imports must return an error message."""
    tool = SafePythonTool(timeout=10)
    result = tool._run("import subprocess")
    assert "Error" in result or "blocked" in result.lower()


def test_tool_timeout() -> None:
    """Infinite loop must be caught by timeout."""
    tool = SafePythonTool(timeout=2)
    result = tool._run("while True: pass")
    assert "timeout" in result.lower() or "Error" in result


def test_tool_custom_params() -> None:
    """Custom timeout and strategy must be respected."""
    tool = SafePythonTool(timeout=20, strategy="subprocess", allow_network=True)
    assert tool.timeout == 20
    assert tool.strategy == "subprocess"
    assert tool.allow_network
