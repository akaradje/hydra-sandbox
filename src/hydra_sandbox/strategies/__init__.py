"""
Strategy registry with auto-detection.

At import time, probes which strategies are available on this platform
and caches the result so ``execute_python(strategy="auto")`` can pick
the strongest available without repeated probing.
"""

from __future__ import annotations

import logging
from typing import Any

from .subprocess_strategy import SubprocessStrategy
from .seccomp_strategy import SeccompStrategy
from .landlock_strategy import LandlockStrategy

logger = logging.getLogger(__name__)

_STRATEGIES: dict[str, type[Any]] = {
    "subprocess": SubprocessStrategy,
    "seccomp": SeccompStrategy,
    "landlock": LandlockStrategy,
}

# Probe once at import time
_AVAILABLE: dict[str, bool] = {
    "subprocess": True,
    "seccomp": SeccompStrategy.is_available(),
    "landlock": LandlockStrategy.is_available(),
}

_seccomp_landlock_available: bool = _AVAILABLE["seccomp"] and _AVAILABLE["landlock"]

logger.debug("Available strategies: %s", [k for k, v in _AVAILABLE.items() if v])


def get_strategy(name: str) -> object:
    """Return a strategy instance for the given *name*.

    Args:
        name: One of ``"auto"``, ``"subprocess"``, ``"seccomp"``,
            ``"landlock"``, or ``"seccomp+landlock"``.

    Returns:
        A strategy instance.
    """
    if name == "auto":
        return _auto_detect()

    if name == "seccomp+landlock":
        if _seccomp_landlock_available:
            return _CompositeStrategy(
                seccomp=SeccompStrategy(),
                landlock=LandlockStrategy(),
            )
        logger.warning(
            "seccomp+landlock requested but not fully available "
            "(seccomp=%s, landlock=%s). Falling back to best available.",
            _AVAILABLE["seccomp"],
            _AVAILABLE["landlock"],
        )
        return _auto_detect()

    cls = _STRATEGIES.get(name)
    if cls is None:
        valid = ["auto", "subprocess", "seccomp", "landlock", "seccomp+landlock"]
        raise ValueError(f"Unknown strategy {name!r}; valid: {valid}")

    if name != "subprocess" and not _AVAILABLE.get(name):
        logger.warning(
            "Strategy %r is not available on this platform. Falling back to subprocess.",
            name,
        )
        return SubprocessStrategy()

    return cls()


def _auto_detect() -> object:
    """Pick the strongest available strategy."""
    if _seccomp_landlock_available:
        logger.info("Auto-detected strategy: seccomp+landlock")
        return _CompositeStrategy(
            seccomp=SeccompStrategy(),
            landlock=LandlockStrategy(),
        )
    if _AVAILABLE["seccomp"]:
        logger.info("Auto-detected strategy: seccomp")
        return SeccompStrategy()
    logger.info("Auto-detected strategy: subprocess")
    return SubprocessStrategy()


def available_strategies() -> list[str]:
    """Return list of strategy names available on this platform."""
    result = ["subprocess"]
    if _AVAILABLE["seccomp"]:
        result.append("seccomp")
    if _AVAILABLE["landlock"]:
        result.append("landlock")
    if _seccomp_landlock_available:
        result.append("seccomp+landlock")
    return result


class _CompositeStrategy:
    """Combines seccomp and landlock into a single strategy."""

    name = "seccomp+landlock"

    def __init__(self, seccomp: SeccompStrategy, landlock: LandlockStrategy) -> None:
        self._seccomp = seccomp
        self._landlock = landlock

    def prepare_preamble(self, allow_network: bool) -> list[str]:
        return self._seccomp.prepare_preamble(allow_network)

    def configure_subprocess(self) -> dict:
        kwargs: dict = {}

        def _combined_preexec() -> None:
            from .subprocess_strategy import _preexec_fn_posix

            _preexec_fn_posix()

            # Install seccomp (import from its module to avoid duplication)
            from .seccomp_strategy import _install_seccomp_filter

            _install_seccomp_filter()

            # Then install landlock
            self._landlock._install_landlock()

        kwargs["preexec_fn"] = _combined_preexec
        return kwargs

    def extract_blocked_imports(self, stderr: str) -> list[str]:
        return self._seccomp.extract_blocked_imports(stderr)

    def cleanup(self) -> None:
        self._seccomp.cleanup()
        self._landlock.cleanup()

    def set_sandbox_dir(self, path: str) -> None:
        self._landlock.set_sandbox_dir(path)
