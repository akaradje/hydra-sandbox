"""
Seccomp strategy — kernel-level syscall filtering (Linux only).

Uses ``libseccomp`` via ``pyseccomp`` (or raw ctypes) to install a
BPF filter that whitelists safe syscalls and kills the process on
dangerous ones (execve, fork, socket, ptrace, etc.).

**Prerequisites**::

    apt install libseccomp-dev   # Debian/Ubuntu
    brew install libseccomp      # macOS (no kernel support; for dev only)
    pip install hydra-pysandbox[seccomp]
"""

from __future__ import annotations

import errno
import logging
import os
import re
import sys

from hydra_sandbox import guard as _guard

from .base import SandboxStrategy
from .subprocess_strategy import _preexec_fn_posix

logger = logging.getLogger(__name__)

# Syscalls whitelisted for Python execution
_SAFE_SYSCALLS = [
    "read", "write", "open", "openat", "close",
    "mmap", "munmap", "mprotect",
    "brk", "exit", "exit_group",
    "rt_sigaction", "rt_sigprocmask", "sigreturn",
    "futex", "getpid", "gettid", "clock_gettime",
    "clock_getres", "gettimeofday",
    "getcwd", "stat", "fstat", "lstat", "newfstatat",
    "access", "readlink",
    "lseek", "pread64", "pwrite64",
    "getdents64", "getrandom",
    "arch_prctl", "set_tid_address", "set_robust_list",
    "rseq", "prlimit64",
    "madvise", "getrusage",
    "tgkill", "sched_getaffinity",
]

# Syscalls blocked unconditionally (KILL on invocation)
_KILL_SYSCALLS = [
    "execve", "execveat", "fork", "vfork", "clone", "clone3",
    "socket", "connect", "accept", "accept4", "bind", "listen",
    "ptrace", "personality",
    "mount", "umount2",
    "chmod", "chown",
    "init_module", "finit_module", "delete_module",
    "kexec_load", "kexec_file_load",
    "iopl", "ioperm",
    "setuid", "setgid",
    "process_vm_writev",
    "bpf", "seccomp",
]


def _install_seccomp_filter() -> None:
    """Install a seccomp-bpf filter in the current (child) process.

    Tries ``pyseccomp`` first; falls back to ctypes if unavailable.
    """
    try:
        import pyseccomp as seccomp

        f = seccomp.SyscallFilter(seccomp.ERRNO(errno.EPERM))

        for sc in _SAFE_SYSCALLS:
            try:
                f.add_rule(seccomp.ALLOW, sc)
            except Exception:
                pass

        for sc in _KILL_SYSCALLS:
            try:
                f.add_rule(seccomp.KILL, sc)
            except Exception:
                pass

        f.load()
        return
    except ImportError:
        pass

    # Fallback: ctypes direct invocation
    try:
        _install_seccomp_ctypes()
    except Exception:
        logger.warning("seccomp unavailable — falling back to Python-level isolation")


def _install_seccomp_ctypes() -> None:
    """Minimal seccomp via ctypes (best-effort, subset of syscalls)."""
    import ctypes
    import ctypes.util

    libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)

    SYS_FORK = 57
    SYS_VFORK = 58
    SYS_CLONE = 56
    SYS_EXECVE = 59
    SYS_SOCKET = 41
    SYS_CONNECT = 42

    KILL_SYSCALLS_CTYPES = [SYS_FORK, SYS_VFORK, SYS_CLONE, SYS_EXECVE, SYS_SOCKET, SYS_CONNECT]

    PR_SET_SECCOMP = 22
    SECCOMP_MODE_FILTER = 2
    SECCOMP_RET_KILL = 0x00000000
    SECCOMP_RET_ALLOW = 0x7FFF0000

    class SockFprog(ctypes.Structure):
        _fields_ = [("len", ctypes.c_ushort), ("filter", ctypes.c_void_p)]

    class SockFilter(ctypes.Structure):
        _fields_ = [("code", ctypes.c_uint16), ("jt", ctypes.c_uint8), ("jf", ctypes.c_uint8), ("k", ctypes.c_uint32)]

    filters = []
    for sc in KILL_SYSCALLS_CTYPES:
        filters.append(SockFilter(0x20, 0, 0, sc))  # load syscall number
        filters.append(SockFilter(0x15, 0, 1, SECCOMP_RET_KILL))  # compare + kill if match
    filters.append(SockFilter(0x06, 0, 0, SECCOMP_RET_ALLOW))  # allow everything else

    prog = SockFprog(len(filters), ctypes.cast((SockFilter * len(filters))(*filters), ctypes.c_void_p))
    libc.prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, ctypes.byref(prog))


class SeccompStrategy:
    """Sandbox strategy that adds kernel-level syscall filtering.

    Extends the subprocess strategy's import guard and network block
    with a seccomp-bpf filter installed in the child before execution.

    **Linux only** with ``libseccomp`` available.
    """

    name = "seccomp"

    def prepare_preamble(self, allow_network: bool) -> list[str]:
        from .subprocess_strategy import SubprocessStrategy

        return SubprocessStrategy().prepare_preamble(allow_network)

    def configure_subprocess(self) -> dict:
        kwargs: dict = {}

        def _combined_preexec() -> None:
            _preexec_fn_posix()
            _install_seccomp_filter()

        kwargs["preexec_fn"] = _combined_preexec
        return kwargs

    def extract_blocked_imports(self, stderr: str) -> list[str]:
        from .subprocess_strategy import SubprocessStrategy

        return SubprocessStrategy().extract_blocked_imports(stderr)

    def cleanup(self) -> None:
        pass

    @classmethod
    def is_available(cls) -> bool:
        """Return True if seccomp is usable on this platform."""
        if sys.platform != "linux":
            return False
        try:
            import pyseccomp  # noqa: F401

            return True
        except ImportError:
            pass
        import ctypes.util

        return ctypes.util.find_library("c") is not None
