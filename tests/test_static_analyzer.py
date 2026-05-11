"""
AST signature verification tests.
"""

from __future__ import annotations

import pytest

from hydra_sandbox import extract_expected_signature, verify_ast_signature


# ---------------------------------------------------------------------------
# verify_ast_signature — success cases
# ---------------------------------------------------------------------------


def test_valid_module_level_function_passes() -> None:
    """A module-level function with correct signature must pass."""
    code = "def foo(x, y):\n    return x + y\n"
    result = verify_ast_signature(code, "foo", ["x", "y"])
    assert result is None


def test_single_param_function() -> None:
    """Function with single parameter must pass."""
    code = "def bar(data: bytes) -> bool:\n    return len(data) > 0\n"
    result = verify_ast_signature(code, "bar", ["data"])
    assert result is None


def test_no_param_function() -> None:
    """Function with no parameters must pass."""
    code = "def get_version():\n    return '1.0'\n"
    result = verify_ast_signature(code, "get_version", [])
    assert result is None


def test_async_function_passes() -> None:
    """Async function at module level must pass."""
    code = "async def fetch(url: str) -> dict:\n    return {}\n"
    result = verify_ast_signature(code, "fetch", ["url"])
    assert result is None


# ---------------------------------------------------------------------------
# verify_ast_signature — failure cases
# ---------------------------------------------------------------------------


def test_function_inside_class_fails() -> None:
    """Function defined inside a class must fail with clear error."""
    code = """
class Calculator:
    def compute(self, x, y):
        return x + y
"""
    result = verify_ast_signature(code, "compute", ["x", "y"])
    assert result is not None
    assert "inside class" in result.lower()
    assert "Calculator" in result


def test_missing_function_fails() -> None:
    """When the expected function is not found, must return error."""
    code = "def other_func():\n    pass\n"
    result = verify_ast_signature(code, "my_func", [])
    assert result is not None
    assert "not found" in result.lower()


def test_signature_mismatch_fails() -> None:
    """Wrong parameter names must be caught."""
    code = "def process(a, b, c):\n    return a + b + c\n"
    result = verify_ast_signature(code, "process", ["x", "y", "z"])
    assert result is not None
    assert "Signature mismatch" in result


def test_wrong_number_of_params_fails() -> None:
    """Wrong number of parameters must be caught."""
    code = "def process(a, b):\n    return a + b\n"
    result = verify_ast_signature(code, "process", ["a", "b", "c"])
    assert result is not None
    assert "Signature mismatch" in result


def test_syntax_error_surfaced() -> None:
    """Syntax errors must be surfaced with line number."""
    code = "def broken(: pass\n"
    result = verify_ast_signature(code, "broken", [])
    assert result is not None
    assert "Syntax error" in result
    assert "line" in result.lower()


def test_no_fatal_prefix() -> None:
    """Error messages must NOT contain 'FATAL:' prefix."""
    code = "class Wrapper:\n    def inner(x):\n        pass\n"
    result = verify_ast_signature(code, "inner", ["x"])
    assert result is not None
    assert "FATAL:" not in result


# ---------------------------------------------------------------------------
# extract_expected_signature
# ---------------------------------------------------------------------------


def test_extract_pattern_a_full_signature() -> None:
    """Pattern A: full function signature in single quotes."""
    desc = "Write a function 'add(a: int, b: int) -> int' that adds two numbers"
    sig = extract_expected_signature(desc)
    assert sig == ("add", ["a", "b"])


def test_extract_pattern_a_no_types() -> None:
    """Pattern A: signature without type annotations."""
    desc = "Implement 'multiply(x, y)' returning the product"
    sig = extract_expected_signature(desc)
    assert sig == ("multiply", ["x", "y"])


def test_extract_pattern_a_double_quotes() -> None:
    """Pattern A: signature in double quotes."""
    desc = 'function named "process(data, config)" should handle input'
    sig = extract_expected_signature(desc)
    assert sig == ("process", ["data", "config"])


def test_extract_pattern_b_parameters_keyword() -> None:
    """Pattern B: 'func_name' with parameters (...) syntax."""
    desc = "function 'calculate' with parameters (x, y, z)"
    sig = extract_expected_signature(desc)
    assert sig == ("calculate", ["x", "y", "z"])


def test_extract_no_signature_returns_none() -> None:
    """Description without signature pattern must return None."""
    desc = "Write a program that sorts a list"
    sig = extract_expected_signature(desc)
    assert sig is None


def test_extract_empty_description() -> None:
    """Empty description must return None."""
    assert extract_expected_signature("") is None
