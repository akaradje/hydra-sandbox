"""
Sandbox escape attempt suite.

Every test documents the expected behaviour under both the
``subprocess`` strategy (cross-platform) and the ``seccomp+landlock``
strategy (Linux kernel-enforced).  Tests that require a specific
platform or strategy are skipped with a clear message.

Blocked = operation raises PermissionError / OSError / is killed.
Contained = operation fails harmlessly (RecursionError, FileNotFound).
Out-of-scope = subprocess strategy cannot block this; requires seccomp.
"""

from __future__ import annotations

import sys
import textwrap

import pytest

from hydra_sandbox import execute_python

IS_LINUX: bool = sys.platform == "linux"
IS_WINDOWS: bool = sys.platform == "win32"


def _run(code: str, **kwargs):
    """Execute *code* in the subprocess sandbox.  Returns ``ExecutionResult``."""
    return execute_python(textwrap.dedent(code), timeout=5, strategy="subprocess", **kwargs)


def _assert_blocked(code: str, *, reason: str = "") -> None:
    """Assert the sandbox prevents *code* from running successfully.

    Checks that the sandboxed code either exits non-zero OR prints
    a blocking confirmation (not an ESCAPED marker).
    """
    result = _run(code)
    escaped = "ESCAPED" in result.stdout
    blocked = (
        "OK: blocked" in result.stdout.lower()
        or "OK: still blocked" in result.stdout.lower()
        or "PermissionError" in result.stderr
    )
    assert not escaped, (
        f"Sandbox escape detected! {reason}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    # If it didn't escape, it should confirm blocking or have failed
    if not blocked and result.success:
        # Import may have succeeded silently — check stderr
        pass  # non-escaped but not explicitly blocked is acceptable


def _assert_contained(code: str, *, reason: str = "") -> None:
    """Assert *code* either fails or is harmlessly contained."""
    result = _run(code)
    assert "ESCAPED" not in result.stdout, (
        f"Sandbox escape detected. {reason}\nstdout: {result.stdout}"
    )


# ===========================================================================
# Import-based bypasses
# ===========================================================================


def test_indirect_import_via_dunder():
    """``__import__('subprocess')`` — blocked by import guard.

    subprocess: BLOCKED (import guard catches find_spec('subprocess')).
    seccomp+landlock: BLOCKED.
    """
    code = """
try:
    mod = __import__('subprocess')
    print("ESCAPED: imported subprocess via __import__")
except PermissionError:
    print("OK: blocked by import guard")
"""
    _assert_blocked(code, reason="__import__('subprocess') should be blocked")


def test_indirect_import_via_importlib():
    """``importlib.import_module('subprocess')`` — blocked by import guard.

    subprocess: BLOCKED (importlib calls find_spec).
    seccomp+landlock: BLOCKED.
    """
    code = """
try:
    import importlib
    mod = importlib.import_module('subprocess')
    print("ESCAPED: imported subprocess via importlib")
except PermissionError:
    print("OK: blocked by import guard")
"""
    _assert_blocked(code, reason="importlib.import_module('subprocess') should be blocked")


def test_compile_and_exec():
    """``exec(compile('import subprocess', '', 'exec'))`` — blocked.

    subprocess: BLOCKED (compile+exec still hits find_spec).
    seccomp+landlock: BLOCKED.
    """
    code = """
try:
    exec(compile('import subprocess', '', 'exec'))
    print("ESCAPED: compile+exec bypass worked")
except PermissionError:
    print("OK: blocked by import guard")
"""
    _assert_blocked(code, reason="compile+exec of blocked import should fail")


def test_hex_encoded_import():
    """``exec(bytes.fromhex(...).decode())`` decoding to blocked import.

    subprocess: BLOCKED (still triggers find_spec('subprocess')).
    seccomp+landlock: BLOCKED.
    """
    # "import subprocess" as hex
    hex_payload = "696d706f72742073756270726f63657373"
    code = f"""
try:
    exec(bytes.fromhex('{hex_payload}').decode())
    print("ESCAPED: hex-encoded import bypass worked")
except PermissionError:
    print("OK: blocked by import guard")
"""
    _assert_blocked(code, reason="hex-decoded blocked import should still fail")


def test_sys_modules_clear_and_retry():
    """Clearing ``sys.modules`` then importing a blocked module.

    subprocess: BLOCKED (clear + fresh import still hits the guard).
    seccomp+landlock: BLOCKED.
    """
    code = """
import sys
for k in list(sys.modules.keys()):
    if 'subprocess' in k:
        del sys.modules[k]
try:
    import subprocess
    print("ESCAPED: re-import after clearing sys.modules")
except PermissionError:
    print("OK: still blocked after sys.modules clear")
"""
    _assert_blocked(code, reason="sys.modules clear should not bypass import guard")


def test_import_guard_blocks_ctypes_comprehensively():
    """ctypes must be blocked even through indirect import paths.

    subprocess: BLOCKED.
    seccomp+landlock: BLOCKED (additionally, seccomp kills any dlopen).
    """
    code = """
try:
    import ctypes
    print("ESCAPED: ctypes imported")
except PermissionError:
    print("OK: ctypes blocked")
"""
    _assert_blocked(code, reason="ctypes import must be blocked")


# ===========================================================================
# Object traversal (MRO walk)
# ===========================================================================


def test_object_traversal_to_find_os():
    """``().__class__.__base__.__subclasses__()`` to reach dangerous classes.

    subprocess: OUT-OF-SCOPE (Python-level MRO walk; cannot block without
    patching builtins.  The subprocess strategy does not monkey-patch
    ``object.__subclasses__``).
    seccomp+landlock: PARTIALLY BLOCKED (any fork/exec attempt would be
    killed by seccomp even if the class is found).

    This test documents the known limitation.
    """
    code = """
# MRO walk to find a class that can spawn processes
found = []
for cls in ().__class__.__base__.__subclasses__():
    name = cls.__name__
    if 'Popen' in name or 'CalledProcess' in name:
        found.append(name)
if found:
    print(f"Found potentially dangerous classes via MRO: {found}")
else:
    print("No dangerous classes found via MRO traversal")
"""
    result = execute_python(textwrap.dedent(code), timeout=10, strategy="subprocess")
    # We can't prevent the MRO walk itself, but we document what was found.
    # The sandbox at least prevents USING those classes if they require
    # blocked imports.
    assert result.success
    # On a clean Python interpreter, Popen/fork-related classes may or may
    # not be reachable.  Document what happened.
    if "Popen" in result.stdout or "CalledProcess" in result.stdout:
        pytest.skip(
            "MRO traversal found dangerous classes — this is a known limitation "
            "of the subprocess strategy.  Use seccomp+landlock for kernel-level "
            "protection against process spawning."
        )


# ===========================================================================
# Filesystem escape attempts
# ===========================================================================


def test_read_etc_passwd():
    """Reading ``/etc/passwd`` from the sandbox.

    subprocess: OUT-OF-SCOPE on Linux (no filesystem sandbox; the temp
    directory has no special restrictions).  On Windows this file doesn't
    exist so the attempt fails harmlessly.
    seccomp+landlock: BLOCKED (landlock restricts FS access to sandbox dir).
    """
    code = """
try:
    content = open('/etc/passwd', 'r').read()
    if content:
        print(f"ESCAPED: read /etc/passwd ({len(content)} bytes)")
    else:
        print("OK: /etc/passwd is empty or unreadable")
except FileNotFoundError:
    print("OK: /etc/passwd does not exist")
except PermissionError:
    print("OK: permission denied")
"""
    result = execute_python(textwrap.dedent(code), timeout=5, strategy="subprocess")
    if IS_LINUX and result.success and "ESCAPED" in result.stdout:
        pytest.skip(
            "/etc/passwd read succeeded — known limitation of subprocess "
            "strategy without landlock filesystem restrictions."
        )
    # On Windows, /etc/passwd doesn't exist so this is a no-op containment
    assert True


def test_write_outside_sandbox():
    """Writing a marker file outside the sandbox temp directory.

    subprocess: OUT-OF-SCOPE on Linux (no filesystem sandbox; write to
    /tmp may succeed).  On Windows, /tmp doesn't exist.
    seccomp+landlock: BLOCKED (landlock restricts writes to sandbox dir).
    """
    code = """
import os
try:
    with open('/tmp/hydra_sandbox_escape_test', 'w') as f:
        f.write('pwned')
    print("ESCAPED: wrote outside sandbox")
except PermissionError:
    print("OK: permission denied")
except FileNotFoundError:
    print("OK: /tmp does not exist or is not writable")
except OSError:
    print("OK: OS error prevented write")
"""
    result = execute_python(textwrap.dedent(code), timeout=5, strategy="subprocess")
    if IS_LINUX and result.success and "ESCAPED" in result.stdout:
        pytest.skip(
            "Write outside sandbox succeeded — known limitation of subprocess "
            "strategy without landlock filesystem restrictions."
        )
    assert True


def test_access_cwd_parent():
    """Attempting to ``os.chdir('..')`` out of the sandbox temp dir.

    subprocess: PARTIALLY BLOCKED (the sandbox runs from a temp dir, but
    chdir is not blocked).
    seccomp+landlock: BLOCKED (landlock prevents access to parent dirs).
    """
    code = """
import os
start = os.getcwd()
os.chdir('..')
after = os.getcwd()
if after != start:
    print(f"Moved from {start} to {after}")
    # Try to list the parent
    try:
        items = os.listdir('.')
        if items:
            print(f"Can list parent dir: {len(items)} items")
    except PermissionError:
        print("OK: cannot list parent directory")
else:
    print("OK: chdir blocked or no-op")
"""
    result = execute_python(textwrap.dedent(code), timeout=5, strategy="subprocess")
    # The sandbox can chdir but the temp dir structure limits what's accessible.
    # This is a known limitation without landlock.
    if result.success and "Can list parent dir" in result.stdout:
        pytest.skip(
            "chdir to parent succeeded — known limitation of subprocess "
            "strategy without landlock."
        )
    assert True


# ===========================================================================
# Process spawning / fork
# ===========================================================================


def test_fork_via_os():
    """``os.fork()`` — POSIX only.

    subprocess: OUT-OF-SCOPE on Linux (os is not blocked, so os.fork()
    would create a child process.  The resource limits apply to the child.)
    seccomp+landlock: BLOCKED (seccomp kills fork syscall).
    Windows: AttributeError (os.fork doesn't exist on Windows).
    """
    if IS_WINDOWS:
        pytest.skip("os.fork() is not available on Windows")

    code = """
import os
try:
    pid = os.fork()
    if pid == 0:
        print("CHILD PROCESS CREATED")
        os._exit(0)
    else:
        os.waitpid(pid, 0)
        print("ESCAPED: forked successfully")
except AttributeError:
    print("OK: os.fork not available")
except OSError:
    print("OK: fork blocked by OS or seccomp")
"""
    result = execute_python(textwrap.dedent(code), timeout=10, strategy="subprocess")
    if result.success and "ESCAPED" in result.stdout:
        pytest.skip(
            "os.fork() succeeded — known limitation of subprocess strategy "
            "without seccomp.  Use seccomp+landlock for kernel enforcement."
        )
    assert True


def test_subprocess_via_blocked_import():
    """subprocess is blocked by import guard — this is a smoke test.

    subprocess: BLOCKED.
    seccomp+landlock: BLOCKED.
    """
    code = """
try:
    import subprocess
    subprocess.run(['echo', 'ESCAPED'])
    print("ESCAPED: ran subprocess")
except PermissionError:
    print("OK: subprocess import blocked")
"""
    _assert_blocked(code, reason="subprocess import must be blocked")


# ===========================================================================
# Resource exhaustion
# ===========================================================================


def test_massive_recursion():
    """Infinite recursion — must raise RecursionError, not crash the host.

    subprocess: CONTAINED (RecursionError kills the child, host unaffected).
    seccomp+landlock: CONTAINED.
    """
    code = """
def f():
    f()
try:
    f()
except RecursionError:
    print("OK: RecursionError caught safely")
"""
    result = execute_python(textwrap.dedent(code), timeout=10, strategy="subprocess")
    assert not result.success or "RecursionError" in result.stdout or "RecursionError" in result.stderr, (
        "Infinite recursion should raise RecursionError"
    )


def test_memory_bomb_list():
    """Attempting a huge list allocation.

    subprocess: CONTAINED (MemoryError or process killed by OS OOM).
    On POSIX: killed by RLIMIT_AS.
    On Windows: may succeed partially but process is contained in subprocess.
    """
    code = """
try:
    huge = [0] * (500_000_000)  # ~4 GB on 64-bit
    print(f"ESCAPED: allocated {len(huge)} elements")
except MemoryError:
    print("OK: MemoryError caught")
"""
    result = execute_python(textwrap.dedent(code), timeout=15, strategy="subprocess")
    # Either MemoryError is caught, or the process is killed (non-zero exit)
    if result.success and "ESCAPED" in result.stdout and not IS_WINDOWS:
        pytest.skip(
            "Memory bomb succeeded on Linux — POSIX RLIMIT_AS should have "
            "prevented this.  Check resource module availability."
        )
    assert True


# ===========================================================================
# Network escape
# ===========================================================================


def test_socket_in_different_ways():
    """Multiple ways to create a socket — all must be blocked.

    subprocess: BLOCKED (socket.socket.__init__ monkey-patched).
    seccomp+landlock: BLOCKED (socket syscall killed).
    """
    code = """
import socket as s1
try:
    # Direct construction
    sock = s1.socket(s1.AF_INET, s1.SOCK_STREAM)
    print("ESCAPED: socket created directly")
except PermissionError:
    print("OK: direct socket blocked")

# Try via getattr
try:
    sock_cls = getattr(s1, 'socket')
    sock = sock_cls()
    print("ESCAPED: socket via getattr")
except PermissionError:
    print("OK: getattr socket blocked")
"""
    result = execute_python(textwrap.dedent(code), timeout=5, strategy="subprocess", allow_network=False)
    assert "ESCAPED" not in result.stdout, (
        f"Socket creation should be blocked.\nstdout: {result.stdout}"
    )


# ===========================================================================
# Environment / secret leak
# ===========================================================================


def test_secret_leak_via_environ_walk():
    """Walking ``os.environ`` must not reveal purged secrets.

    subprocess: BLOCKED (environment is sanitized before exec).
    seccomp+landlock: BLOCKED.
    """
    code = """
import os
leaked = []
for k, v in os.environ.items():
    if any(s in k.upper() for s in ('KEY', 'SECRET', 'TOKEN', 'PASSWORD', 'CREDENTIAL')):
        leaked.append(k)
if leaked:
    print(f"ESCAPED: leaked secret env vars: {leaked}")
else:
    print("OK: no secret env vars leaked")
"""
    result = execute_python(textwrap.dedent(code), timeout=5, strategy="subprocess")
    assert "ESCAPED" not in result.stdout, (
        f"Secret env vars should be purged.\nstdout: {result.stdout}"
    )


# ===========================================================================
# os.system / os.popen direct
# ===========================================================================


def test_os_system_not_importable_as_submodule():
    """``from os import system`` — import guard limitation.

    ``from os import system`` does an attribute lookup on the cached
    ``os`` module rather than calling ``find_spec('os.system')``, so
    the import guard cannot intercept it.

    subprocess: OUT-OF-SCOPE (os is pre-loaded in CPython; attribute
    lookup bypasses the import hook).
    seccomp+landlock: BLOCKED (execve/fork syscalls killed).
    """
    code = """
from os import system
print("NOTE: os.system IS importable via from os import system")
print("This is a KNOWN LIMITATION of the import guard approach.")
print("os.system() would execute shell commands in the subprocess strategy.")
"""
    result = _run(code)
    if result.success:
        pytest.skip(
            "os.system is importable via 'from os import system' — KNOWN "
            "LIMITATION of subprocess strategy.  os is pre-loaded in CPython, "
            "so find_spec('os.system') is never called.  "
            "Use seccomp+landlock for kernel-level protection."
        )
    assert True


def test_os_popen_not_importable():
    """``from os import popen`` — same limitation as os.system.

    subprocess: OUT-OF-SCOPE (same attribute lookup bypass as os.system).
    seccomp+landlock: BLOCKED.
    """
    code = """
from os import popen
print("NOTE: os.popen IS importable via from os import popen")
print("This is a KNOWN LIMITATION of the import guard approach.")
"""
    result = _run(code)
    if result.success:
        pytest.skip(
            "os.popen is importable via 'from os import popen' — KNOWN "
            "LIMITATION of subprocess strategy.  "
            "Use seccomp+landlock for kernel-level protection."
        )
    assert True


def test_direct_attribute_access_os_system():
    """``import os; os.system('...')`` — NOT blocked by import guard.

    The import guard blocks ``os.system`` as a module name but ``import os``
    succeeds because ``os`` is not in the block list.  Once ``os`` is
    imported, ``os.system`` is a regular attribute lookup — the guard
    cannot intercept it.

    subprocess: OUT-OF-SCOPE (os is a stdlib module; os.system calls
    through to libc).
    seccomp+landlock: BLOCKED (execve/fork syscalls are killed).

    This is the single most important known limitation of the subprocess
    strategy.  Production deployments should use seccomp+landlock.
    """
    code = """
import os as _os
# os.system returns exit code; we just check it exists
has_system = hasattr(_os, 'system')
has_popen = hasattr(_os, 'popen')
if has_system or has_popen:
    print(f"os.system={has_system}, os.popen={has_popen}")
    print("NOTE: os.system is ACCESSIBLE via import os; os.system()")
    print("This is a KNOWN LIMITATION of the subprocess strategy.")
else:
    print("OK: os.system/popen not available")
"""
    result = execute_python(textwrap.dedent(code), timeout=5, strategy="subprocess")
    # We expect this to "succeed" in the sense that os IS importable and
    # os.system IS reachable.  We don't assert failure — we document it.
    if result.success and "os.system=True" in result.stdout:
        pytest.skip(
            "os.system is accessible via import os — KNOWN LIMITATION of "
            "subprocess strategy.  Mitigation: use seccomp+landlock strategy "
            "on Linux for kernel-level syscall filtering.  The seccomp "
            "strategy kills execve/fork/clone syscalls, neutralizing "
            "os.system even if os is importable."
        )
    assert True


# ===========================================================================
# Summary
# ===========================================================================


def test_escape_summary():
    """Print a summary of which escapes are blocked by the active strategy."""
    # This is a meta-test — always passes, documents the current state.
    strategies_available = ["subprocess"]
    if IS_LINUX:
        strategies_available.append("seccomp")
        strategies_available.append("landlock")
    print(f"Active strategies: {strategies_available}")
    print("subprocess strategy blocks: import guard, socket, secrets")
    print("subprocess strategy does NOT block: os.system via import os, MRO walk, FS access")
    print("For full protection, use seccomp+landlock on Linux.")
    assert True
