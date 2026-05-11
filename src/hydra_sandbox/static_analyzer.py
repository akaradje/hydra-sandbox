"""
Deterministic AST-based signature validator.

Runs BEFORE sandbox execution.  Catches structural errors (wrong
function name, wrong parameters, class-instead-of-function) using
Python's built-in ``ast`` module — zero external cost, zero latency.
"""

from __future__ import annotations

import ast


def verify_ast_signature(
    code_string: str,
    expected_func: str,
    expected_args: list[str],
) -> str | None:
    """Verify *expected_func* is defined at module level with exact *expected_args*.

    Returns ``None`` if the code passes all checks.
    Returns a human-readable error string on any structural violation.
    """

    # 1. Parse — surface syntax errors immediately
    try:
        tree = ast.parse(code_string)
    except SyntaxError as exc:
        return f"Syntax error in generated code at line {exc.lineno}: {exc.msg}"

    # 2. Check for the function inside a class (forbidden for standalone)
    class_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            class_names.add(node.name)
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if item.name == expected_func:
                        return (
                            f"'{expected_func}' is defined inside class "
                            f"'{node.name}'. The spec requires a standalone "
                            f"module-level function with no classes."
                        )

    # 3. Find the function at module level
    func_def: ast.FunctionDef | ast.AsyncFunctionDef | None = None
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == expected_func:
                func_def = node
                break

    if func_def is None:
        found = ", ".join(sorted(class_names)) if class_names else "none"
        return (
            f"Function '{expected_func}' not found at module level. "
            f"(Classes found: {found})"
        )

    # 4. Extract parameter names (skip *args, **kwargs, and 'self')
    actual_args: list[str] = []
    for arg in func_def.args.args:
        if arg.arg == "self":
            continue
        actual_args.append(arg.arg)

    # 5. Exact parameter-name match
    if actual_args != expected_args:
        return (
            f"Signature mismatch for '{expected_func}':\n"
            f"  Expected: ({', '.join(expected_args)})\n"
            f"  Got:      ({', '.join(actual_args)})\n"
            f"  Fix parameter names and order to match the spec exactly."
        )

    return None


def extract_expected_signature(description: str) -> tuple[str, list[str]] | None:
    """Best-effort extraction of ``(func_name, [arg_names])`` from a task description.

    Recognises patterns like:

    * ``function 'verify_zclaw_mint(tx_data: bytes, proof: list, root: bytes)'``
    * ``named 'verify_zclaw_mint' with parameters (tx_data, proof, root)``
    * ``'my_func(a, b, c)'``

    Returns ``None`` if no unambiguous signature could be extracted.
    """
    import re

    # Pattern A:  named 'func_name(p1: type1, p2: type2)' — full signature
    m = re.search(
        r"""(?:function\s+)?(?:named\s+)?['"](\w+)\s*\(([^)]*)\)\s*(?:->\s*\w+)?""",
        description,
    )
    if m:
        func_name = m.group(1)
        raw_args = m.group(2)
        args = [a.split(":")[0].strip() for a in raw_args.split(",") if a.strip()]
        return func_name, args

    # Pattern B:  'func_name' ... parameters (a, b, c)
    m = re.search(
        r"""['"](\w+)['"].*?parameters?\s*\(([^)]+)\)""",
        description,
    )
    if m:
        func_name = m.group(1)
        raw_args = m.group(2)
        args = [a.strip() for a in raw_args.split(",") if a.strip()]
        return func_name, args

    return None
