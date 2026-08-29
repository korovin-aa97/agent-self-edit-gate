"""Guarded checks and atomic mutation operations."""

from __future__ import annotations

import os
import secrets
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import GateError
from .policy import Policy, Target, resolve_target, sha256
from .receipts import ReceiptJournal, operation_pairs, read_records


@dataclass(frozen=True)
class FileState:
    exists: bool
    content: bytes
    mode: int
    uid: int | None
    gid: int | None
    device: int | None
    inode: int | None


def _open_parent(policy: Policy, target: Target) -> int:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor: int | None = None
    try:
        descriptor = os.open(policy.root, flags)
        for part in Path(target.relative).parent.parts:
            if part == ".":
                continue
            next_descriptor = os.open(part, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_descriptor
        return descriptor
    except OSError as exc:
        if descriptor is not None:
            os.close(descriptor)
        raise GateError("E_PARENT_RACE", f"cannot anchor target parent: {exc}") from exc


def _read_state(parent_fd: int, name: str, max_bytes: int) -> FileState:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(name, flags, dir_fd=parent_fd)
    except FileNotFoundError:
        return FileState(False, b"", 0o600, None, None, None, None)
    except OSError as exc:
        raise GateError("E_TARGET_OPEN", f"cannot safely open target: {exc}") from exc
    with os.fdopen(descriptor, "rb") as stream:
        metadata = os.fstat(stream.fileno())
        if not stat.S_ISREG(metadata.st_mode):
            raise GateError("E_TARGET_TYPE", "target must be a regular file")
        if metadata.st_uid != os.geteuid():
            raise GateError("E_TARGET_OWNER", "target is not owned by this user")
        content = stream.read(max_bytes + 1)
        if len(content) > max_bytes:
            raise GateError("E_SIZE", f"existing file exceeds max_bytes={max_bytes}")
        return FileState(
            True,
            content,
            stat.S_IMODE(metadata.st_mode),
            metadata.st_uid,
            metadata.st_gid,
            metadata.st_dev,
            metadata.st_ino,
        )


def _changed_bytes(before: bytes, after: bytes) -> int:
    prefix = 0
    limit = min(len(before), len(after))
    while prefix < limit and before[prefix] == after[prefix]:
        prefix += 1
    suffix = 0
    before_left = len(before) - prefix
    after_left = len(after) - prefix
    while (
        suffix < before_left
        and suffix < after_left
        and before[len(before) - suffix - 1] == after[len(after) - suffix - 1]
    ):
        suffix += 1
    return (len(before) - prefix - suffix) + (len(after) - prefix - suffix)


def _validate_content(policy: Policy, state: FileState, content: bytes) -> int:
    if len(content) > policy.max_bytes:
        raise GateError("E_SIZE", f"content exceeds max_bytes={policy.max_bytes}")
    if b"\x00" in content:
        raise GateError("E_BINARY", "NUL bytes are forbidden in behaviour files")
    try:
        content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GateError("E_ENCODING", "content must be valid UTF-8") from exc
    if not state.exists and not policy.allow_create:
        raise GateError("E_CREATE_DENIED", "policy does not allow new files")
    changed = _changed_bytes(state.content, content)
    if changed > policy.max_changed_bytes:
        raise GateError(
            "E_DIFF_SIZE",
            f"change exceeds max_changed_bytes={policy.max_changed_bytes} ({changed})",
        )
    return changed


def _assert_same_state(parent_fd: int, name: str, expected: FileState) -> None:
    try:
        metadata = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError as exc:
        if expected.exists:
            raise GateError("E_TARGET_RACE", "target disappeared during the operation") from exc
        return
    except OSError as exc:
        raise GateError("E_TARGET_RACE", f"cannot re-check target: {exc}") from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise GateError("E_TARGET_RACE", "target type changed during the operation")
    if not expected.exists:
        raise GateError("E_TARGET_RACE", "target appeared during the operation")
    if (metadata.st_dev, metadata.st_ino, metadata.st_uid) != (
        expected.device,
        expected.inode,
        expected.uid,
    ):
        raise GateError("E_TARGET_RACE", "target identity changed during the operation")


def _atomic_replace(parent_fd: int, name: str, expected: FileState, content: bytes) -> None:
    _assert_same_state(parent_fd, name, expected)
    temp_name = f".{name}.selfedit-{secrets.token_hex(8)}"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor: int | None = None
    try:
        descriptor = os.open(temp_name, flags, expected.mode, dir_fd=parent_fd)
        with os.fdopen(descriptor, "wb", closefd=True) as stream:
            descriptor = None
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
            if expected.exists and expected.uid is not None and expected.gid is not None:
                try:
                    os.fchown(stream.fileno(), expected.uid, expected.gid)
                except PermissionError:
                    pass
            os.fchmod(stream.fileno(), expected.mode)
        _assert_same_state(parent_fd, name, expected)
        os.replace(temp_name, name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
        os.fsync(parent_fd)
    except GateError:
        raise
    except OSError as exc:
        raise GateError("E_ATOMIC_WRITE", f"atomic write failed: {exc}") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            os.unlink(temp_name, dir_fd=parent_fd)
        except FileNotFoundError:
            pass
        except OSError:
            pass


def check(policy: Policy, raw_target: str) -> dict[str, Any]:
    target = resolve_target(policy, raw_target)
    exists = target.path.exists()
    return {
        "path": target.relative,
        "zone": target.zone.name,
        "mutable": True,
        "exists": exists,
        "creation_allowed": policy.allow_create,
        "policy_sha256": policy.sha256,
    }


def guarded_write(
    policy: Policy,
    raw_target: str,
    content: bytes,
    *,
    action: str,
    expected_before_sha256: str | None = None,
) -> dict[str, Any]:
    target = resolve_target(policy, raw_target)
    parent_fd = _open_parent(policy, target)
    try:
        with ReceiptJournal(policy) as journal:
            state = _read_state(parent_fd, target.path.name, policy.max_bytes)
            before_hash = sha256(state.content)
            if expected_before_sha256 is not None and expected_before_sha256 != before_hash:
                raise GateError("E_TARGET_STALE", "target changed before replacement")
            changed = _validate_content(policy, state, content)
            policy.assert_unchanged()
            operation_id = secrets.token_hex(16)
            common = {
                "operation_id": operation_id,
                "action": action,
                "path": target.relative,
                "zone": target.zone.name,
                "policy_sha256": policy.sha256,
                "before_sha256": before_hash,
                "proposed_after_sha256": sha256(content),
                "content_bytes": len(content),
                "changed_bytes": changed,
            }
            journal.append({**common, "phase": "intent"})
            policy.assert_unchanged()
            _atomic_replace(parent_fd, target.path.name, state, content)
            journal.append(
                {
                    **common,
                    "phase": "commit",
                    "after_sha256": sha256(content),
                }
            )
        return {
            "operation_id": operation_id,
            "path": target.relative,
            "action": action,
            "before_sha256": before_hash,
            "after_sha256": sha256(content),
            "changed_bytes": changed,
        }
    finally:
        os.close(parent_fd)


def exact_replace(policy: Policy, raw_target: str, old: bytes, new: bytes) -> dict[str, Any]:
    if not old:
        raise GateError("E_EMPTY_ANCHOR", "replacement anchor is empty")
    target = resolve_target(policy, raw_target)
    parent_fd = _open_parent(policy, target)
    try:
        state = _read_state(parent_fd, target.path.name, policy.max_bytes)
    finally:
        os.close(parent_fd)
    if not state.exists:
        raise GateError("E_NOT_FOUND", "replace target does not exist")
    count = state.content.count(old)
    if count != 1:
        raise GateError("E_ANCHOR_COUNT", f"replacement anchor matched {count} times")
    return guarded_write(
        policy,
        raw_target,
        state.content.replace(old, new, 1),
        action="replace",
        expected_before_sha256=sha256(state.content),
    )


def verify_receipts(policy: Policy, *, check_files: bool = True) -> dict[str, Any]:
    policy.assert_unchanged()
    records = read_records(policy)
    latest: dict[str, str] = {}
    operations = 0
    for intent, commit in operation_pairs(records):
        operations += 1
        if intent.get("policy_sha256") != policy.sha256:
            raise GateError(
                "E_POLICY_MISMATCH",
                f"operation {intent['operation_id']} used a different policy hash",
            )
        if commit is None:
            raise GateError(
                "E_DANGLING_INTENT",
                f"operation {intent['operation_id']} has no commit receipt",
            )
        fields = (
            "action",
            "path",
            "zone",
            "policy_sha256",
            "before_sha256",
            "proposed_after_sha256",
            "content_bytes",
            "changed_bytes",
        )
        if any(intent.get(field) != commit.get(field) for field in fields):
            raise GateError(
                "E_RECEIPT_PAIR", f"operation {intent['operation_id']} intent/commit differ"
            )
        if commit.get("after_sha256") != intent.get("proposed_after_sha256"):
            raise GateError(
                "E_RECEIPT_PAIR", f"operation {intent['operation_id']} has wrong after hash"
            )
        path = intent.get("path")
        if not isinstance(path, str):
            raise GateError("E_RECEIPT_FIELDS", "receipt path is missing")
        if path in latest and intent.get("before_sha256") != latest[path]:
            raise GateError("E_FILE_CHAIN", f"file hash chain breaks for {path}")
        latest[path] = str(commit["after_sha256"])
    if check_files:
        for raw_target, expected_hash in latest.items():
            target = resolve_target(policy, raw_target)
            parent_fd = _open_parent(policy, target)
            try:
                state = _read_state(parent_fd, target.path.name, policy.max_bytes)
            finally:
                os.close(parent_fd)
            if not state.exists or sha256(state.content) != expected_hash:
                raise GateError("E_CURRENT_HASH", f"current file hash differs for {raw_target}")
    return {
        "valid": True,
        "records": len(records),
        "operations": operations,
        "files": len(latest),
        "policy_sha256": policy.sha256,
        "current_files_checked": check_files,
    }
