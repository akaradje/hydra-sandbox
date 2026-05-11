"""
Optional, opt-in telemetry for install-base visibility.

Sends ONLY: package version + strategy selected on first execution.
No user code, no environment variables, no PII.

Disabled by default.  Opt in with ``HYDRA_SANDBOX_TELEMETRY=1``.
Disable explicitly with ``HYDRA_SANDBOX_NO_TELEMETRY=1``.
"""

from __future__ import annotations

import logging
import os
import urllib.request
from urllib.error import URLError

logger = logging.getLogger(__name__)

_TELEMETRY_ENDPOINT = "https://telemetry.hydra-sandbox.dev/ping"
_SENT_FLAG = False


def _telemetry_enabled() -> bool:
    """Return True only if the user has explicitly opted in."""
    if os.environ.get("HYDRA_SANDBOX_NO_TELEMETRY", "").strip() == "1":
        return False
    return os.environ.get("HYDRA_SANDBOX_TELEMETRY", "").strip() == "1"


def _ping_once(strategy: str) -> None:
    """Send a single install ping.  Throttled to once per process."""
    global _SENT_FLAG
    if _SENT_FLAG or not _telemetry_enabled():
        return
    _SENT_FLAG = True

    from hydra_sandbox._version import __version__

    payload = f"v={__version__}&strategy={strategy}&os=python"
    try:
        req = urllib.request.Request(
            f"{_TELEMETRY_ENDPOINT}?{payload}",
            method="GET",
        )
        urllib.request.urlopen(req, timeout=3.0)
        logger.debug("Telemetry ping sent: %s", payload)
    except (URLError, OSError):
        logger.debug("Telemetry ping failed (expected if endpoint is down)")
