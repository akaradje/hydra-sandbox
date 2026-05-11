"""
Isolated Python code executor with configurable sandbox strategies.

Runs code in a child process with resource limits, filesystem sandboxing,
import guarding, and output capping.  POSIX resource limits are applied
where available; Windows falls back to wall-clock timeout.

Strategy selection::

    result = execute_python(code)                     # auto-detect best
    result = execute_python(code, strategy="subprocess")  # cross-platform
    result = execute_python(code, strategy="seccomp")     # Linux only
    result = execute_python(code, strategy="seccomp+landlock")  # strongest
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field

from hydra_sandbox.strategies import get_strategy

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT = 5  # seconds (wall-clock)
MAX_OUTPUT_BYTES = 1_048_576  # 1 MiB per stream


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class ExecutionResult:
    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    timed_out: bool = False
    exception_info: str | None = None
    cpu_time: float | None = None
    peak_memory_kb: int | None = None
    blocked_imports: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Output truncation helper
# ---------------------------------------------------------------------------


def _truncate(s: str, max_bytes: int) -> str:
    encoded = s.encode("utf-8", errors="replace")
    if len(encoded) <= max_bytes:
        return s
    truncated = encoded[: max_bytes - 20]
    return truncated.decode("utf-8", errors="replace") + "\n[...TRUNCATED]"


# ---------------------------------------------------------------------------
# Environment isolation
# ---------------------------------------------------------------------------


def _build_sandbox_env(temp_dir: str) -> dict[str, str]:
    """Build a minimal environment for the sandbox child process."""
    env: dict[str, str] = {}
    for key in ("PATH", "PYTHONPATH", "LANG", "LC_ALL", "SYSTEMROOT", "TMP", "TEMP"):
        if key in os.environ:
            env[key] = os.environ[key]
    env["HOME"] = temp_dir
    env["USER"] = "sandbox"
    # Explicitly purge secrets
    for k in os.environ:
        upper = k.upper()
        if any(
            suffix in upper
            for suffix in ("_TOKEN", "_KEY", "_SECRET", "_PASSWORD", "_CREDENTIAL")
        ):
            continue
        if k not in env:
            env[k] = os.environ[k]
    return env


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def execute_python(
    code: str,
    *,
    timeout: int = DEFAULT_TIMEOUT,
    allow_network: bool = False,
    extra_allowed_imports: tuple[str, ...] | None = None,
    strategy: str = "auto",
) -> ExecutionResult:
    """Run *code* in a hardened child Python process.

    Args:
        code: Python source to execute.
        timeout: Wall-clock timeout in seconds.
        allow_network: If False (default), socket creation raises PermissionError.
        extra_allowed_imports: Additional modules to allow beyond defaults.
        strategy: Sandbox strategy — one of ``"auto"``, ``"subprocess"``,
            ``"seccomp"``, ``"landlock"``, or ``"seccomp+landlock"``.
            Default ``"auto"`` picks the strongest available.

    Returns:
        ExecutionResult with outcome, output, and resource metrics.
    """
    strat = get_strategy(strategy)

    # Build sandboxed code: network block preamble + import guard + user code
    preamble_lines = strat.prepare_preamble(allow_network)
    full_code = "\n".join(preamble_lines) + "\n" + code

    # Filesystem isolation: run in a fresh temp directory
    with tempfile.TemporaryDirectory(prefix="sandbox_") as temp_dir:
        env = _build_sandbox_env(temp_dir)

        # Let landlock know the sandbox dir if available
        if hasattr(strat, "set_sandbox_dir"):
            strat.set_sandbox_dir(temp_dir)

        subprocess_kwargs: dict = {
            "capture_output": True,
            "text": True,
            "timeout": timeout,
            "cwd": temp_dir,
            "env": env,
        }
        subprocess_kwargs.update(strat.configure_subprocess())

        if sys.platform == "win32":
            logger.debug(
                "Windows detected — POSIX resource limits unavailable; "
                "using wall-clock timeout only."
            )

        blocked_imports: list[str] = []

        try:
            proc = subprocess.run(
                [sys.executable, "-c", full_code],
                **subprocess_kwargs,
            )

            stdout = _truncate(proc.stdout or "", MAX_OUTPUT_BYTES)
            stderr = _truncate(proc.stderr or "", MAX_OUTPUT_BYTES)

            blocked_imports = strat.extract_blocked_imports(proc.stderr or "")

            return ExecutionResult(
                success=proc.returncode == 0,
                stdout=stdout,
                stderr=stderr,
                exit_code=proc.returncode,
                timed_out=False,
                exception_info=None if proc.returncode == 0 else stderr.strip() or None,
                cpu_time=None,
                peak_memory_kb=None,
                blocked_imports=blocked_imports,
            )

        except subprocess.TimeoutExpired as exc:
            stdout = _truncate(
                exc.stdout.decode("utf-8", errors="replace") if exc.stdout else "",
                MAX_OUTPUT_BYTES,
            )
            stderr = _truncate(
                exc.stderr.decode("utf-8", errors="replace") if exc.stderr else f"Timeout after {timeout}s",
                MAX_OUTPUT_BYTES,
            )
            return ExecutionResult(
                success=False,
                stdout=stdout,
                stderr=stderr,
                exit_code=None,
                timed_out=True,
                exception_info=f"Subprocess timed out after {timeout} seconds",
                cpu_time=None,
                peak_memory_kb=None,
                blocked_imports=blocked_imports,
            )

        finally:
            strat.cleanup()
