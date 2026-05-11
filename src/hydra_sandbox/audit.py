"""
Tamper-evident audit trail with Merkle hash chaining.

Every recorded operation generates an entry that links to the
previous entry via a SHA-256 hash, forming a verifiable chain.
Tampering with any entry breaks the chain and is detected by
``verify_chain()``.

Pure stdlib — no external dependencies.

Usage::

    audit = AuditLog("audit.jsonl")
    with audit.record("execute_python") as entry:
        result = execute_python(code)
        entry.add("code_hash", sha256(code))
        entry.add("success", result.success)
    audit.verify_chain()  # True
"""

from __future__ import annotations

import csv
import hashlib
import json
import logging
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class AuditEntry:
    """A single audit trail entry, created inside a ``with audit.record(...)`` block."""

    def __init__(self, operation: str) -> None:
        self.operation = operation
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self._data: dict[str, Any] = {}
        self._prev_hash: str | None = None
        self._final_hash: str | None = None

    def add(self, key: str, value: Any) -> None:
        """Record a key-value data point for this audit entry."""
        self._data[key] = value

    def _seal(self, prev_hash: str | None) -> str:
        """Compute and store the hash for this entry; return it."""
        self._prev_hash = prev_hash
        payload = {
            "timestamp": self.timestamp,
            "operation": self.operation,
            "prev_hash": prev_hash,
            "data": self._data,
        }
        serialized = json.dumps(payload, sort_keys=True, default=str)
        self._final_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        return self._final_hash

    def to_dict(self) -> dict[str, Any]:
        """Return the entry as a JSON-serialisable dict."""
        return {
            "timestamp": self.timestamp,
            "operation": self.operation,
            "prev_hash": self._prev_hash,
            "hash": self._final_hash,
            "data": self._data,
        }


class AuditLog:
    """JSONL-based audit trail with Merkle hash chaining.

    Each entry is written as one line of JSON.  The hash of each entry
    includes the hash of the previous entry, forming a chain that
    detects tampering.
    """

    def __init__(self, path: str | Path = "audit.jsonl") -> None:
        self._path = Path(path)
        self._entries: list[AuditEntry] = []
        self._last_hash: str | None = None

        # Load existing entries to compute last hash on startup
        if self._path.exists():
            with open(self._path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        try:
                            entry = json.loads(line)
                            self._last_hash = entry.get("hash")
                        except json.JSONDecodeError:
                            pass

    @contextmanager
    def record(self, operation: str) -> Any:
        """Context manager that creates an ``AuditEntry``, writes it on exit.

        Usage::

            with audit.record("execute_python") as entry:
                entry.add("code_hash", sha256(code))
        """
        entry = AuditEntry(operation)
        yield entry
        entry_hash = entry._seal(self._last_hash)
        self._last_hash = entry_hash
        self._entries.append(entry)
        self._write_entry(entry)

    def _write_entry(self, entry: AuditEntry) -> None:
        """Append one entry to the JSONL file."""
        with open(self._path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry.to_dict(), default=str) + "\n")

    def verify_chain(self) -> bool:
        """Recompute hashes for all entries and verify chain integrity.

        Returns ``True`` if every entry's hash matches its successor's
        ``prev_hash`` and no entry has been modified.
        """
        entries = self._load_entries()
        if not entries:
            return True  # empty log is trivially valid

        prev_hash: str | None = None

        for i, entry in enumerate(entries):
            # Recompute what this entry's hash SHOULD be
            payload = {
                "timestamp": entry.get("timestamp", ""),
                "operation": entry.get("operation", ""),
                "prev_hash": prev_hash,
                "data": entry.get("data", {}),
            }
            serialized = json.dumps(payload, sort_keys=True, default=str)
            expected = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

            actual = entry.get("hash", "")
            if expected != actual:
                logger.error(
                    "Audit chain broken at entry %d: expected hash %s, got %s",
                    i,
                    expected[:16],
                    actual[:16],
                )
                return False

            # Verify prev_hash matches
            if i > 0 and entry.get("prev_hash") != prev_hash:
                logger.error(
                    "Audit chain broken at entry %d: prev_hash mismatch",
                    i,
                )
                return False

            prev_hash = expected

        return True

    def export_csv(self, path: str | Path) -> None:
        """Export the audit trail to a CSV file.

        Columns: index, timestamp, operation, prev_hash, hash, data_keys
        """
        entries = self._load_entries()
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["index", "timestamp", "operation", "prev_hash", "hash", "data_keys"])
            for i, entry in enumerate(entries):
                writer.writerow([
                    i,
                    entry.get("timestamp", ""),
                    entry.get("operation", ""),
                    (entry.get("prev_hash") or "")[:16],
                    (entry.get("hash") or "")[:16],
                    ", ".join(entry.get("data", {}).keys()),
                ])

    def _load_entries(self) -> list[dict[str, Any]]:
        """Load all entries from the JSONL file."""
        if not self._path.exists():
            return []
        entries: list[dict[str, Any]] = []
        with open(self._path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        logger.warning("Skipping malformed audit line: %s", line[:80])
        return entries

    def __len__(self) -> int:
        return len(self._load_entries())
