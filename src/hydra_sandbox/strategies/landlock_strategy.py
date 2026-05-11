"""
Landlock strategy — kernel-level filesystem access control (Linux 5.13+).

Restricts filesystem access to the sandbox temp directory so even
if code escapes the Python-level guards, it cannot read or write
outside the designated area.

**Prerequisites**::

    pip install hydra-sandbox[landlock]
"""

from __future__ import annotations

import logging
import os
import re
import sys

from .base import SandboxStrategy
from .subprocess_strategy import _preexec_fn_posix

logger = logging.getLogger(__name__)


class LandlockStrategy:
    """Sandbox strategy that adds Landlock filesystem sandboxing.

    Restricts filesystem access to a designated temp directory.
    Must be combined with another strategy (typically seccomp) for
    complete isolation.

    **Linux 5.13+ only** with the ``landlock`` Python package.
    """

    name = "landlock"

    def __init__(self) -> None:
        self._sandbox_dir: str | None = None

    def set_sandbox_dir(self, path: str) -> None:
        """Tell landlock which directory the sandbox is allowed to access."""
        self._sandbox_dir = path

    def _install_landlock(self) -> None:
        if self._sandbox_dir is None:
            return

        try:
            import landlock

            rules = landlock.Ruleset()
            rules.allow(
                self._sandbox_dir,
                access=landlock.ACCESS_READ | landlock.ACCESS_WRITE,
            )
            if sys.executable:
                rules.allow(
                    sys.executable,
                    access=landlock.ACCESS_READ | landlock.ACCESS_EXECUTE,
                )
            rules.restrict_self()
        except ImportError:
            logger.warning("landlock package not installed — skipping filesystem sandbox")
        except Exception as exc:
            logger.warning("landlock restriction failed: %s", exc)

    def prepare_preamble(self, allow_network: bool) -> list[str]:
        from .subprocess_strategy import SubprocessStrategy

        return SubprocessStrategy().prepare_preamble(allow_network)

    def configure_subprocess(self) -> dict:
        kwargs: dict = {}

        def _combined_preexec() -> None:
            _preexec_fn_posix()
            self._install_landlock()

        kwargs["preexec_fn"] = _combined_preexec
        return kwargs

    def extract_blocked_imports(self, stderr: str) -> list[str]:
        from .subprocess_strategy import SubprocessStrategy

        return SubprocessStrategy().extract_blocked_imports(stderr)

    def cleanup(self) -> None:
        pass

    @classmethod
    def is_available(cls) -> bool:
        """Return True if Landlock is usable on this platform."""
        if sys.platform != "linux":
            return False
        try:
            import landlock  # noqa: F401

            return True
        except ImportError:
            return False
