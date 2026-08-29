"""Policy-enforced writes for agent behaviour files."""

from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import hashlib
import json
import os
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Zone:
    """One ordered policy zone."""

    name: str
    mode: str
    patterns: tuple[str, ...]
    extensions: tuple[str, ...]


@dataclass(frozen=True)
class Policy:
    """Loaded repository write policy."""

    root: Path
    receipt_log: Path
    max_bytes: int
    zones: tuple[Zone, ...]
    sha256: str


class GateError(RuntimeError):
    """A refused or invalid write."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_policy(path: Path) -> Policy:
    raw = path.read_bytes()
    data = tomllib.loads(raw.decode("utf-8"))
    gate = data.get("gate", {})
    policy_dir = path.resolve().parent
    root_value = Path(str(gate.get("root", ".")))
    root = (policy_dir / root_value).resolve()
    receipt_value = Path(str(gate.get("receipt_log", ".selfedit-gate/receipts.jsonl")))
    receipt_log = receipt_value if receipt_value.is_absolute() else root / receipt_value
    zones = tuple(
        Zone(
            name=str(item["name"]),
            mode=str(item["mode"]),
            patterns=tuple(str(value) for value in item.get("patterns", [])),
            extensions=tuple(str(value) for value in item.get("extensions", [])),
        )
        for item in data.get("zones", [])
    )
    return Policy(
        root=root,
        receipt_log=receipt_log,
        max_bytes=int(gate.get("max_bytes", 262_144)),
        zones=zones,
        sha256=_sha(raw),
    )


def resolve_target(policy: Policy, raw: str) -> tuple[Path, str]:
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = policy.root / candidate
    resolved = candidate.parent.resolve() / candidate.name
    if resolved.is_symlink():
        raise GateError("target is a symlink")
    try:
        relative = resolved.relative_to(policy.root).as_posix()
    except ValueError as exc:
        raise GateError("target resolves outside the policy root") from exc
    return resolved, relative


def classify(policy: Policy, relative: str) -> Zone:
    matches: list[Zone] = []
    for zone in policy.zones:
        if any(fnmatch.fnmatch(relative, pattern) for pattern in zone.patterns):
            matches.append(zone)
    immutable = next((zone for zone in matches if zone.mode == "immutable"), None)
    if immutable is not None:
        raise GateError(f"{relative} is immutable ({immutable.name})")
    mutable = next((zone for zone in matches if zone.mode == "mutable"), None)
    if mutable is None:
        raise GateError(f"{relative} is not in a mutable zone")
    if mutable.extensions and Path(relative).suffix not in mutable.extensions:
        raise GateError(f"extension is not allowed by zone {mutable.name}")
    return mutable


def append_receipt(policy: Policy, record: dict[str, Any]) -> None:
    policy.receipt_log.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, sort_keys=True) + "\n"
    with policy.receipt_log.open("a", encoding="utf-8") as stream:
        stream.write(line)
        stream.flush()
        os.fsync(stream.fileno())


def atomic_write(target: Path, content: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, raw_path = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    temp_path = Path(raw_path)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        temp_path.replace(target)
    finally:
        temp_path.unlink(missing_ok=True)


def guarded_write(policy: Policy, target: Path, relative: str, content: bytes) -> None:
    if len(content) > policy.max_bytes:
        raise GateError(f"content exceeds max_bytes={policy.max_bytes}")
    classify(policy, relative)
    before = target.read_bytes() if target.exists() else b""
    operation_id = hashlib.sha256(
        f"{relative}:{dt.datetime.now(dt.UTC).isoformat()}".encode()
    ).hexdigest()[:16]
    base = {
        "operation_id": operation_id,
        "path": relative,
        "policy_sha256": policy.sha256,
        "before_sha256": _sha(before),
    }
    append_receipt(policy, {**base, "phase": "intent"})
    atomic_write(target, content)
    append_receipt(policy, {**base, "phase": "commit", "after_sha256": _sha(content)})


def command_check(args: argparse.Namespace) -> int:
    policy = load_policy(args.policy)
    _, relative = resolve_target(policy, args.target)
    zone = classify(policy, relative)
    print(f"mutable: {relative} ({zone.name})")
    return 0


def command_replace(args: argparse.Namespace) -> int:
    policy = load_policy(args.policy)
    target, relative = resolve_target(policy, args.target)
    before = target.read_text(encoding="utf-8")
    old = args.old_file.read_text(encoding="utf-8")
    new = args.new_file.read_text(encoding="utf-8")
    if not old:
        raise GateError("replacement anchor is empty")
    count = before.count(old)
    if count != 1:
        raise GateError(f"replacement anchor matched {count} times")
    guarded_write(policy, target, relative, before.replace(old, new, 1).encode())
    print(f"updated: {relative}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="selfedit-gate")
    parser.add_argument(
        "--policy", type=Path, default=Path("selfedit-policy.toml")
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    check = subparsers.add_parser("check")
    check.add_argument("target")
    check.set_defaults(handler=command_check)
    replace = subparsers.add_parser("replace")
    replace.add_argument("target")
    replace.add_argument("old_file", type=Path)
    replace.add_argument("new_file", type=Path)
    replace.set_defaults(handler=command_replace)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.handler(args))
    except (GateError, OSError, KeyError, ValueError, tomllib.TOMLDecodeError) as exc:
        raise SystemExit(f"selfedit-gate: {exc}") from exc
