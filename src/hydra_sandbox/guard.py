"""
Import guard — produces a Python preamble that restricts dangerous imports.

When prepended to sandbox code, this snippet installs itself as
``sys.meta_path[0]`` and blocks the listed modules from being imported.
"""

from __future__ import annotations

from typing import Iterable

# Modules and functions permanently blocked from sandbox code.
_DEFAULT_BLOCK: tuple[str, ...] = (
    "os.system",
    "os.popen",
    "subprocess",
    "ctypes",
    "http.client",
    "urllib",
    "requests",
    "multiprocessing",
    "shutil",
    "signal",
    "ptrace",
    "fcntl",
)

# Modules that are safe by default (stdlib building blocks).
_DEFAULT_ALLOW: tuple[str, ...] = (
    "math",
    "json",
    "hashlib",
    "collections",
    "itertools",
    "functools",
    "typing",
    "dataclasses",
    "re",
    "string",
    "enum",
    "datetime",
    "decimal",
    "fractions",
    "random",
    "statistics",
    "heapq",
    "bisect",
    "array",
    "struct",
    "copy",
    "pprint",
    "textwrap",
    "unittest",
    "warnings",
    "traceback",
    "logging",
    "io",
    "csv",
    "base64",
    "binascii",
    "zlib",
    "gzip",
    "uuid",
    "pathlib",
)


def build_guarded_preamble(allow: Iterable[str] | None = None) -> str:
    """Return a Python snippet that guards imports in the sandbox child.

    Args:
        allow: Additional modules to allow beyond the defaults.

    Returns:
        A string of Python code to prepend to the sandbox code.
    """
    allowed = set(_DEFAULT_ALLOW)
    if allow:
        allowed.update(allow)

    block_list = repr(list(_DEFAULT_BLOCK))

    preamble = f'''\
import sys as _sandbox_sys

_BLOCK = {block_list}

class _ImportGuard:
    def find_spec(self, fullname, path, target=None):
        for blocked in _BLOCK:
            if fullname == blocked or fullname.startswith(blocked + "."):
                if not hasattr(_sandbox_sys, "_sandbox_blocked_imports"):
                    _sandbox_sys._sandbox_blocked_imports = []
                if fullname not in _sandbox_sys._sandbox_blocked_imports:
                    _sandbox_sys._sandbox_blocked_imports.append(fullname)
                raise PermissionError(
                    f"Import blocked by sandbox: {{fullname}}"
                )
        return None

_sandbox_sys.meta_path.insert(0, _ImportGuard())
'''
    return preamble
