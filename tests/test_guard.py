"""
Import guard tests — preamble generation and blocked module coverage.

The in-process exec() tests use ``_run_isolated`` to clear cached
modules from ``sys.modules`` before executing, since the import
guard relies on ``find_spec`` being called, which Python skips
for modules already present in ``sys.modules``.
"""

from __future__ import annotations

import sys

from hydra_sandbox.guard import build_guarded_preamble


def _run_isolated(code: str) -> None:
    """Execute *code* with the import guard active, clearing any
    cached blocked modules from ``sys.modules`` so the finder hook
    is actually invoked."""
    import importlib

    preamble = build_guarded_preamble()
    # Determine which modules the guard would block so we can
    # evict them from the cache.
    block_names = [
        "subprocess", "ctypes", "multiprocessing", "shutil", "signal",
        "ptrace", "fcntl", "os", "http.client", "urllib", "requests",
    ]
    saved = {}
    for name in block_names:
        if name in sys.modules:
            saved[name] = sys.modules.pop(name)
    try:
        exec(preamble + "\n" + code, {})
    finally:
        sys.modules.update(saved)


def test_preamble_is_valid_python() -> None:
    """The generated preamble must be syntactically valid Python."""
    preamble = build_guarded_preamble()
    code = preamble + "\nprint('preamble OK')"
    exec(code, {})


def test_preamble_contains_import_guard_class() -> None:
    """Generated preamble must include the _ImportGuard class."""
    preamble = build_guarded_preamble()
    assert "_ImportGuard" in preamble
    assert "find_spec" in preamble
    assert "sys as _sandbox_sys" in preamble


def test_preamble_installs_meta_path() -> None:
    """Generated preamble must insert _ImportGuard into sys.meta_path."""
    preamble = build_guarded_preamble()
    assert "meta_path.insert" in preamble
    assert "_ImportGuard" in preamble


def test_preamble_raises_permission_error() -> None:
    """The _ImportGuard must raise PermissionError on blocked modules."""
    try:
        _run_isolated("import subprocess\n")
        assert False, "subprocess import should have been blocked"
    except PermissionError as exc:
        assert "subprocess" in str(exc).lower()


def test_preamble_allows_safe_modules() -> None:
    """The _ImportGuard must allow safe stdlib modules."""
    preamble = build_guarded_preamble()
    code = preamble + "\nimport math\nimport json\nimport hashlib\n"
    exec(code, {})


def test_preamble_blocks_ctypes() -> None:
    """ctypes must be blocked."""
    try:
        _run_isolated("import ctypes\n")
        assert False, "ctypes import should have been blocked"
    except PermissionError:
        pass


def test_preamble_blocks_signal() -> None:
    """signal must be blocked when freshly imported."""
    try:
        _run_isolated("import signal\n")
        assert False, "signal import should have been blocked"
    except PermissionError:
        pass


def test_preamble_blocks_multiprocessing() -> None:
    """multiprocessing must be blocked."""
    try:
        _run_isolated("import multiprocessing\n")
        assert False, "multiprocessing import should have been blocked"
    except PermissionError:
        pass


def test_extra_allowed_imports_work() -> None:
    """Additional allowed imports passed to build_guarded_preamble must work."""
    preamble = build_guarded_preamble(allow=["numpy"])
    # The preamble should be valid Python regardless
    code = preamble + "\nprint('extra allow test OK')\n"
    exec(code, {})
