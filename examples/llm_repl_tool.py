"""
Example: Using hydra-pysandbox as a LangChain / LlamaIndex tool.

This sketch shows how to wrap ``execute_python`` as a tool that an
LLM agent can call to safely run generated or user-submitted code.

Requirements: pip install hydra-pysandbox langchain
"""

from hydra_sandbox import execute_python


def sandbox_python_tool(code: str, timeout: int = 5) -> str:
    """Execute Python code in a hardened sandbox. Safe for LLM agents.

    Args:
        code: Python source to execute.
        timeout: Maximum execution time in seconds.

    Returns:
        Execution output as a string (stdout + stderr).
    """
    result = execute_python(code, timeout=timeout, strategy="auto")
    if result.timed_out:
        return f"Error: code timed out after {timeout} seconds."
    if not result.success:
        return f"Error (exit {result.exit_code}):\n{result.stderr}"
    return result.stdout if result.stdout else "(no output)"


# ---- LangChain integration sketch ----
# from langchain.tools import tool
#
# @tool
# def python_repl(code: str) -> str:
#     """Execute Python code in a secure sandbox. Provide valid Python."""
#     return sandbox_python_tool(code)


if __name__ == "__main__":
    print(sandbox_python_tool("print(2 + 2)"))
    print(sandbox_python_tool("import subprocess"))  # will be blocked
