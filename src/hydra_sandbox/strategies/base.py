"""
Sandbox strategy protocol.

Every strategy must implement ``prepare_preamble`` and ``configure_subprocess``
so the executor can use it without knowing the implementation details.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


class SandboxStrategy(Protocol):
    """Contract for a sandbox isolation strategy."""

    name: str

    def prepare_preamble(self, allow_network: bool) -> list[str]:
        """Return preamble code lines to inject before user code."""
        ...

    def configure_subprocess(
        self,
    ) -> dict:
        """Return kwargs to merge into ``subprocess.run()`` (e.g. ``preexec_fn``)."""
        ...

    def extract_blocked_imports(self, stderr: str) -> list[str]:
        """Parse stderr for blocked-import annotations."""
        ...

    def cleanup(self) -> None:
        """Optional teardown after execution (e.g. remove temp filters)."""
        ...


@dataclass
class StrategyResult:
    """Metadata returned by a strategy after execution."""

    blocked_imports: list[str] = field(default_factory=list)
    cpu_time: float | None = None
    peak_memory_kb: int | None = None
