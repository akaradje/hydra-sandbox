"""
Subprocess strategy — default cross-platform sandbox.

Runs code in a child Python process with import guards, network
blocking (via socket monkey-patching), and resource limits (POSIX).
This is the baseline strategy available on all platforms.
"""

from __future__ import annotations

import os
import re
import sys

from hydra_sandbox import guard as _guard

from .base import SandboxStrategy

# ---------------------------------------------------------------------------
# Network isolation preamble (socket monkey-patching)
# ---------------------------------------------------------------------------

_NETWORK_BLOCK_PREAMBLE = """\
import socket as _sandbox_sock
_sandbox_sock._original_socket_init = _sandbox_sock.socket.__init__
def _sandbox_sock_block(self, *a, **kw):
    raise PermissionError("Network access disabled by sandbox")
_sandbox_sock.socket.__init__ = _sandbox_sock_block
del _sandbox_sock
"""

# ---------------------------------------------------------------------------
# Resource limits
# ---------------------------------------------------------------------------

_DEFAULT_CPU_LIMIT = 30  # seconds (CPU time, POSIX only)
_DEFAULT_MEMORY_MB = 512  # MiB address space limit (POSIX only)
_DEFAULT_NOFILE = 64  # max open files


def _preexec_fn_posix() -> None:
    """Apply resource limits in the child process (POSIX only)."""
    try:
        import resource  # noqa: F811

        try:
            resource.setrlimit(resource.RLIMIT_CPU, (_DEFAULT_CPU_LIMIT, _DEFAULT_CPU_LIMIT))
        except ValueError:
            pass

        mem_bytes = _DEFAULT_MEMORY_MB * 1024 * 1024
        try:
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        except ValueError:
            pass

        try:
            resource.setrlimit(resource.RLIMIT_NOFILE, (_DEFAULT_NOFILE, _DEFAULT_NOFILE))
        except ValueError:
            pass

        try:
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        except ValueError:
            pass

    except ImportError:
        pass


class SubprocessStrategy:
    """Default sandbox strategy using Python-level isolation."""

    name = "subprocess"

    def prepare_preamble(self, allow_network: bool) -> list[str]:
        parts: list[str] = []
        if not allow_network:
            parts.append(_NETWORK_BLOCK_PREAMBLE)
        parts.append(_guard.build_guarded_preamble())
        return parts

    def configure_subprocess(self) -> dict:
        kwargs: dict = {}
        if sys.platform != "win32":
            kwargs["preexec_fn"] = _preexec_fn_posix
        return kwargs

    def extract_blocked_imports(self, stderr: str) -> list[str]:
        blocked: list[str] = []
        for line in stderr.split("\n"):
            if "Import blocked by sandbox" in line:
                m = re.search(r"Import blocked by sandbox: (\S+)", line)
                if m:
                    blocked.append(m.group(1))
        return blocked

    def cleanup(self) -> None:
        pass  # nothing to tear down
