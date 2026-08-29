"""Append-only, hash-chained intent/commit receipt journal."""

from __future__ import annotations

import datetime as dt
import errno
import fcntl
import json
import os
import re
import stat
from collections.abc import Iterator
from typing import Any, BinaryIO

from .errors import GateError
from .policy import Policy, sha256

RECEIPT_SCHEMA_VERSION = 1
GENESIS_HASH = "0" * 64
MAX_JOURNAL_BYTES = 64 * 1024 * 1024


def _canonical(record: dict[str, Any]) -> bytes:
    return json.dumps(record, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode(
        "utf-8"
    )


def _record_hash(record: dict[str, Any]) -> str:
    unsigned = dict(record)
    unsigned.pop("record_sha256", None)
    return sha256(_canonical(unsigned))


def _directory_flags() -> int:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    return flags


def _open_receipt_parent(policy: Policy, *, create: bool) -> int:
    relative = policy.receipt_log.relative_to(policy.root)
    descriptor: int | None = None
    try:
        descriptor = os.open(policy.root, _directory_flags())
        for part in relative.parent.parts:
            if part == ".":
                continue
            try:
                next_descriptor = os.open(part, _directory_flags(), dir_fd=descriptor)
            except FileNotFoundError:
                if not create:
                    raise
                os.mkdir(part, mode=0o700, dir_fd=descriptor)
                os.fsync(descriptor)
                next_descriptor = os.open(part, _directory_flags(), dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_descriptor
        return descriptor
    except GateError:
        if descriptor is not None:
            os.close(descriptor)
        raise
    except FileNotFoundError:
        if descriptor is not None:
            os.close(descriptor)
        raise
    except OSError as exc:
        if descriptor is not None:
            os.close(descriptor)
        code = "E_AUDIT_PATH" if exc.errno in {errno.ELOOP, errno.ENOTDIR} else "E_AUDIT_OPEN"
        raise GateError(code, f"cannot anchor receipt directory: {exc}") from exc


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise GateError("E_AUDIT_JSON", f"duplicate receipt key: {key}")
        result[key] = value
    return result


_HASH = re.compile(r"^[0-9a-f]{64}$")
_OPERATION = re.compile(r"^[0-9a-f]{32}$")


def _validate_fields(record: dict[str, Any], line_number: int) -> None:
    common = {
        "schema_version",
        "sequence",
        "timestamp",
        "previous_record_sha256",
        "record_sha256",
        "operation_id",
        "phase",
        "action",
        "path",
        "zone",
        "policy_sha256",
        "before_sha256",
        "proposed_after_sha256",
        "content_bytes",
        "changed_bytes",
    }
    phase = record.get("phase")
    expected = common | ({"after_sha256"} if phase == "commit" else set())
    if phase not in {"intent", "commit"} or set(record) != expected:
        raise GateError("E_RECEIPT_FIELDS", f"receipt line {line_number} has wrong fields")
    if record.get("action") not in {"write", "replace"}:
        raise GateError("E_RECEIPT_FIELDS", f"receipt line {line_number} has wrong action")
    if not isinstance(record.get("path"), str) or not record["path"]:
        raise GateError("E_RECEIPT_FIELDS", f"receipt line {line_number} has wrong path")
    if not isinstance(record.get("zone"), str) or not record["zone"]:
        raise GateError("E_RECEIPT_FIELDS", f"receipt line {line_number} has wrong zone")
    if not isinstance(record.get("operation_id"), str) or not _OPERATION.fullmatch(
        record["operation_id"]
    ):
        raise GateError("E_RECEIPT_FIELDS", f"receipt line {line_number} has wrong operation_id")
    hash_fields = [
        "previous_record_sha256",
        "record_sha256",
        "policy_sha256",
        "before_sha256",
        "proposed_after_sha256",
    ]
    if phase == "commit":
        hash_fields.append("after_sha256")
    if any(
        not isinstance(record.get(field), str) or not _HASH.fullmatch(record[field])
        for field in hash_fields
    ):
        raise GateError("E_RECEIPT_FIELDS", f"receipt line {line_number} has wrong hash")
    for field in ("content_bytes", "changed_bytes"):
        value = record.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise GateError("E_RECEIPT_FIELDS", f"receipt line {line_number} has wrong {field}")
    timestamp = record.get("timestamp")
    try:
        parsed = dt.datetime.fromisoformat(timestamp) if isinstance(timestamp, str) else None
    except ValueError as exc:
        raise GateError(
            "E_RECEIPT_FIELDS", f"receipt line {line_number} has wrong timestamp"
        ) from exc
    if parsed is None or parsed.tzinfo is None or parsed.utcoffset() != dt.timedelta(0):
        raise GateError("E_RECEIPT_FIELDS", f"receipt line {line_number} has wrong timestamp")


def parse_records(raw: bytes) -> list[dict[str, Any]]:
    """Parse and validate the structural hash chain."""

    if not raw:
        return []
    if len(raw) > MAX_JOURNAL_BYTES:
        raise GateError("E_AUDIT_SIZE", "receipt journal exceeds 64 MiB")
    if not raw.endswith(b"\n"):
        raise GateError("E_AUDIT_TRUNCATED", "receipt journal has a truncated final line")
    records: list[dict[str, Any]] = []
    previous = GENESIS_HASH
    for sequence, line in enumerate(raw.splitlines(), start=1):
        try:
            record = json.loads(line, object_pairs_hook=_no_duplicate_keys)
        except GateError:
            raise
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GateError("E_AUDIT_JSON", f"invalid receipt line {sequence}: {exc}") from exc
        if not isinstance(record, dict):
            raise GateError("E_AUDIT_JSON", f"receipt line {sequence} is not an object")
        if record.get("schema_version") != RECEIPT_SCHEMA_VERSION:
            raise GateError("E_AUDIT_VERSION", f"receipt line {sequence} has unknown schema")
        if record.get("sequence") != sequence:
            raise GateError("E_AUDIT_SEQUENCE", f"receipt line {sequence} has wrong sequence")
        _validate_fields(record, sequence)
        if record.get("previous_record_sha256") != previous:
            raise GateError("E_AUDIT_CHAIN", f"receipt chain breaks at line {sequence}")
        expected = _record_hash(record)
        if record.get("record_sha256") != expected:
            raise GateError("E_AUDIT_HASH", f"receipt hash is invalid at line {sequence}")
        previous = expected
        records.append(record)
    return records


class ReceiptJournal:
    """Exclusive journal transaction covering intent, write, and commit."""

    def __init__(self, policy: Policy) -> None:
        self.policy = policy
        self._stream: BinaryIO | None = None
        self.records: list[dict[str, Any]] = []

    def __enter__(self) -> ReceiptJournal:
        parent_fd = _open_receipt_parent(self.policy, create=True)
        flags = os.O_RDWR | os.O_APPEND | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(self.policy.receipt_log.name, flags, 0o600, dir_fd=parent_fd)
            os.fsync(parent_fd)
            os.close(parent_fd)
            stream = os.fdopen(descriptor, "r+b", buffering=0)
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            metadata = os.fstat(stream.fileno())
            if not stat.S_ISREG(metadata.st_mode):
                raise GateError("E_AUDIT_PATH", "receipt_log is not a regular file")
            if metadata.st_uid != os.geteuid():
                raise GateError("E_AUDIT_OWNER", "receipt_log is not owned by this user")
            if stat.S_IMODE(metadata.st_mode) & 0o022:
                raise GateError("E_AUDIT_MODE", "receipt_log is group/world writable")
            stream.seek(0)
            self.records = parse_records(stream.read(MAX_JOURNAL_BYTES + 1))
            self._stream = stream
            return self
        except GateError:
            try:
                os.close(parent_fd)
            except OSError:
                pass
            if "stream" in locals():
                stream.close()
            raise
        except OSError as exc:
            try:
                os.close(parent_fd)
            except OSError:
                pass
            raise GateError("E_AUDIT_OPEN", f"cannot open receipt journal: {exc}") from exc

    def __exit__(self, *_: object) -> None:
        if self._stream is not None:
            self._stream.close()
            self._stream = None

    def append(self, fields: dict[str, Any]) -> dict[str, Any]:
        if self._stream is None:
            raise RuntimeError("receipt journal is not open")
        previous = self.records[-1]["record_sha256"] if self.records else GENESIS_HASH
        record: dict[str, Any] = {
            "schema_version": RECEIPT_SCHEMA_VERSION,
            "sequence": len(self.records) + 1,
            "timestamp": dt.datetime.now(dt.UTC).isoformat(),
            "previous_record_sha256": previous,
            **fields,
        }
        record["record_sha256"] = _record_hash(record)
        encoded = _canonical(record) + b"\n"
        try:
            self._stream.write(encoded)
            self._stream.flush()
            os.fsync(self._stream.fileno())
        except OSError as exc:
            raise GateError("E_AUDIT_WRITE", f"cannot persist receipt: {exc}") from exc
        self.records.append(record)
        return record


def read_records(policy: Policy) -> list[dict[str, Any]]:
    """Read receipts under a shared advisory lock."""

    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        parent_fd = _open_receipt_parent(policy, create=False)
        try:
            descriptor = os.open(policy.receipt_log.name, flags, dir_fd=parent_fd)
        finally:
            os.close(parent_fd)
        with os.fdopen(descriptor, "rb") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_SH)
            metadata = os.fstat(stream.fileno())
            if not stat.S_ISREG(metadata.st_mode):
                raise GateError("E_AUDIT_PATH", "receipt_log is not a regular file")
            if metadata.st_uid != os.geteuid():
                raise GateError("E_AUDIT_OWNER", "receipt_log is not owned by this user")
            if stat.S_IMODE(metadata.st_mode) & 0o022:
                raise GateError("E_AUDIT_MODE", "receipt_log is group/world writable")
            return parse_records(stream.read(MAX_JOURNAL_BYTES + 1))
    except GateError:
        raise
    except FileNotFoundError:
        return []
    except OSError as exc:
        raise GateError("E_AUDIT_OPEN", f"cannot read receipt journal: {exc}") from exc


def operation_pairs(
    records: list[dict[str, Any]],
) -> Iterator[tuple[dict[str, Any], dict[str, Any] | None]]:
    """Yield ordered intents and their optional commit records."""

    intents: dict[str, dict[str, Any]] = {}
    commits: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for record in records:
        operation_id = record.get("operation_id")
        phase = record.get("phase")
        if not isinstance(operation_id, str):
            raise GateError("E_RECEIPT_FIELDS", "receipt operation_id is missing")
        if phase == "intent":
            if operation_id in intents:
                raise GateError("E_RECEIPT_DUPLICATE", f"duplicate intent {operation_id}")
            intents[operation_id] = record
            order.append(operation_id)
        elif phase == "commit":
            if operation_id not in intents or operation_id in commits:
                raise GateError("E_RECEIPT_ORPHAN", f"orphan/duplicate commit {operation_id}")
            commits[operation_id] = record
        else:
            raise GateError("E_RECEIPT_FIELDS", f"unknown receipt phase {phase!r}")
    for operation_id in order:
        yield intents[operation_id], commits.get(operation_id)
