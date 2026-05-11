"""
hydra-sandbox — Hardened Python execution sandbox.

Provides isolated code execution with configurable strategies
(subprocess, seccomp, landlock), import guarding, AST signature
verification, and optional Z3 formal specification checking.
"""

from hydra_sandbox._version import __version__
from hydra_sandbox.executor import ExecutionResult, execute_python
from hydra_sandbox.guard import build_guarded_preamble
from hydra_sandbox.static_analyzer import extract_expected_signature, verify_ast_signature

__all__ = [
    "execute_python",
    "ExecutionResult",
    "verify_ast_signature",
    "extract_expected_signature",
    "build_guarded_preamble",
    "__version__",
]
