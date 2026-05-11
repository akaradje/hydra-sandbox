"""
Audit trail tests — Merkle hash chaining, tamper detection, CSV export.
"""

from __future__ import annotations

import csv
import json
import os
import tempfile
from pathlib import Path

from hydra_sandbox.audit import AuditEntry, AuditLog


def test_single_entry_no_prev_hash() -> None:
    """First entry in an empty log must have prev_hash=None."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "audit.jsonl"
        audit = AuditLog(path)
        with audit.record("test_op") as entry:
            entry.add("key", "value")
        lines = path.read_text().strip().split("\n")
        data = json.loads(lines[0])
        assert data["prev_hash"] is None
        assert data["operation"] == "test_op"
        assert data["data"]["key"] == "value"
        assert "hash" in data


def test_second_entry_chains_to_first() -> None:
    """Second entry's prev_hash must equal first entry's hash."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "audit.jsonl"
        audit = AuditLog(path)

        with audit.record("first") as e:
            e.add("n", 1)
        with audit.record("second") as e:
            e.add("n", 2)

        lines = path.read_text().strip().split("\n")
        first = json.loads(lines[0])
        second = json.loads(lines[1])
        assert second["prev_hash"] == first["hash"]


def test_verify_chain_empty_is_valid() -> None:
    """An empty audit log must verify as valid."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "empty.jsonl"
        audit = AuditLog(path)
        assert audit.verify_chain()


def test_verify_chain_valid_sequence() -> None:
    """A valid, unmodified chain must verify successfully."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "audit.jsonl"
        audit = AuditLog(path)

        for i in range(5):
            with audit.record(f"op_{i}") as e:
                e.add("i", i)

        assert audit.verify_chain()
        assert len(audit) == 5


def test_tampering_detected_by_verify_chain() -> None:
    """Manually modifying an entry must be detected by verify_chain."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "audit.jsonl"
        audit = AuditLog(path)

        with audit.record("genuine") as e:
            e.add("amount", 100)

        # Tamper: rewrite the file with modified data
        lines = path.read_text().strip().split("\n")
        entry = json.loads(lines[0])
        entry["data"]["amount"] = 99999
        path.write_text(json.dumps(entry) + "\n")

        assert not audit.verify_chain()


def test_tampering_prev_hash_detected() -> None:
    """Changing prev_hash in an entry must invalidate the chain."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "audit.jsonl"
        audit = AuditLog(path)

        with audit.record("first") as e:
            e.add("v", 1)
        with audit.record("second") as e:
            e.add("v", 2)

        # Tamper: change prev_hash of second entry
        lines = path.read_text().strip().split("\n")
        first = json.loads(lines[0])
        second = json.loads(lines[1])
        second["prev_hash"] = "00000000000000000000000000000000deadbeef00000000000000000000"
        path.write_text(
            json.dumps(first) + "\n" + json.dumps(second) + "\n"
        )

        assert not audit.verify_chain()


def test_export_csv() -> None:
    """CSV export must produce a valid CSV file with headers and data rows."""
    with tempfile.TemporaryDirectory() as tmp:
        audit_path = Path(tmp) / "audit.jsonl"
        csv_path = Path(tmp) / "report.csv"
        audit = AuditLog(audit_path)

        with audit.record("test_op") as e:
            e.add("result", "ok")
        with audit.record("another_op") as e:
            e.add("status", 200)

        audit.export_csv(csv_path)
        assert csv_path.exists()

        with open(csv_path, "r", encoding="utf-8") as fh:
            reader = csv.reader(fh)
            rows = list(reader)

        assert len(rows) == 3  # header + 2 data rows
        assert rows[0] == ["index", "timestamp", "operation", "prev_hash", "hash", "data_keys"]
        assert rows[1][2] == "test_op"
        assert rows[2][2] == "another_op"


def test_audit_log_resumes_from_disk() -> None:
    """A new AuditLog pointing to an existing file must pick up the last hash."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "audit.jsonl"

        # First session
        audit1 = AuditLog(path)
        with audit1.record("session1") as e:
            e.add("v", 1)

        # Second session — must chain correctly
        audit2 = AuditLog(path)
        with audit2.record("session2") as e:
            e.add("v", 2)

        assert audit2.verify_chain()
        assert len(audit2) == 2


def test_audit_entry_to_dict() -> None:
    """AuditEntry.to_dict() must return a JSON-serialisable dict."""
    entry = AuditEntry("test_operation")
    entry.add("key", "value")
    entry._seal(None)
    d = entry.to_dict()
    assert d["operation"] == "test_operation"
    assert d["data"]["key"] == "value"
    assert "hash" in d
    json.dumps(d)  # must not raise


def test_audit_log_len() -> None:
    """len(audit) must return the number of entries on disk."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "audit.jsonl"
        audit = AuditLog(path)
        assert len(audit) == 0

        with audit.record("op") as e:
            e.add("n", 1)
        assert len(audit) == 1
