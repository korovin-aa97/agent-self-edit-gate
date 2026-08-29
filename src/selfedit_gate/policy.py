"""Versioned policy loading and deny-before-allow path classification."""

from __future__ import annotations

import hashlib
import os
import re
import stat
import tomllib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .errors import GateError

POLICY_SCHEMA_VERSION = 1
_MODES = frozenset({"mutable", "protected", "immutable"})


def sha256(data: bytes) -> str:
    """Return a lowercase SHA-256 digest."""

    return hashlib.sha256(data).hexdigest()


def _compile_pattern(pattern: str) -> re.Pattern[str]:
    """Compile a gitignore-like path glob where ``*`` never crosses ``/``."""

    if not pattern or pattern.startswith("/"):
        raise GateError("E_POLICY_PATTERN", f"pattern must be relative: {pattern!r}")
    parts = PurePosixPath(pattern).parts
    if ".." in parts or "." in parts:
        raise GateError("E_POLICY_PATTERN", f"pattern is not normalized: {pattern!r}")
    index = 0
    output = ""
    while index < len(pattern):
        char = pattern[index]
        if char == "*":
            if index + 1 < len(pattern) and pattern[index + 1] == "*":
                index += 2
                if index < len(pattern) and pattern[index] == "/":
                    output += "(?:.*/)?"
                    index += 1
                else:
                    output += ".*"
                continue
            output += "[^/]*"
        elif char == "?":
            output += "[^/]"
        else:
            output += re.escape(char)
        index += 1
    return re.compile(f"^{output}$")


@dataclass(frozen=True)
class Zone:
    """One named policy zone."""

    name: str
    mode: str
    patterns: tuple[str, ...]
    extensions: tuple[str, ...]
    _compiled: tuple[re.Pattern[str], ...]

    def matches(self, relative: str) -> bool:
        return any(pattern.fullmatch(relative) for pattern in self._compiled)


@dataclass(frozen=True)
class Target:
    """A target proven to be lexically contained below the policy root."""

    path: Path
    relative: str
    zone: Zone


@dataclass(frozen=True)
class Policy:
    """A validated policy and the hash of its exact source bytes."""

    source: Path
    root: Path
    receipt_log: Path
    max_bytes: int
    max_changed_bytes: int
    allow_create: bool
    zones: tuple[Zone, ...]
    sha256: str

    def assert_unchanged(self) -> None:
        """Fail if the policy changed after the decision was made."""

        try:
            current = self.source.read_bytes()
        except OSError as exc:
            raise GateError("E_POLICY_CHANGED", f"cannot re-read policy: {exc}") from exc
        if sha256(current) != self.sha256:
            raise GateError("E_POLICY_CHANGED", "policy changed during the operation")


def _integer(gate: dict[str, object], name: str, default: int) -> int:
    value = gate.get(name, default)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise GateError("E_POLICY_VALUE", f"gate.{name} must be a positive integer")
    return value


def load_policy(path: Path) -> Policy:
    """Load policy schema v1 and reject unknown or ambiguous semantics."""

    source = path.resolve()
    try:
        raw = source.read_bytes()
        data = tomllib.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise GateError("E_POLICY_READ", f"cannot load policy: {exc}") from exc
    schema_version = data.get("schema_version")
    if type(schema_version) is not int or schema_version != POLICY_SCHEMA_VERSION:
        raise GateError(
            "E_POLICY_VERSION",
            f"policy schema_version must be {POLICY_SCHEMA_VERSION}",
        )
    known_top = {"schema_version", "gate", "zones"}
    unknown_top = sorted(set(data) - known_top)
    if unknown_top:
        raise GateError("E_POLICY_KEY", f"unknown top-level keys: {unknown_top}")
    gate = data.get("gate")
    if not isinstance(gate, dict):
        raise GateError("E_POLICY_VALUE", "[gate] is required")
    known_gate = {
        "root",
        "receipt_log",
        "max_bytes",
        "max_changed_bytes",
        "allow_create",
    }
    unknown_gate = sorted(set(gate) - known_gate)
    if unknown_gate:
        raise GateError("E_POLICY_KEY", f"unknown [gate] keys: {unknown_gate}")

    root_value = gate.get("root", ".")
    receipt_value = gate.get("receipt_log", ".selfedit-gate/receipts.jsonl")
    if not isinstance(root_value, str) or not isinstance(receipt_value, str):
        raise GateError("E_POLICY_VALUE", "root and receipt_log must be strings")
    root_candidate = Path(root_value)
    root = (
        root_candidate.resolve()
        if root_candidate.is_absolute()
        else (source.parent / root_candidate).resolve()
    )
    if not root.is_dir():
        raise GateError("E_POLICY_ROOT", f"policy root is not a directory: {root}")
    receipt_candidate = Path(receipt_value)
    receipt_log = receipt_candidate if receipt_candidate.is_absolute() else root / receipt_candidate
    try:
        receipt_relative = receipt_log.relative_to(root)
    except ValueError as exc:
        raise GateError("E_POLICY_RECEIPTS", "receipt_log must be below policy root") from exc
    if not receipt_relative.parts:
        raise GateError("E_POLICY_RECEIPTS", "receipt_log must name a file below policy root")
    if ".." in receipt_candidate.parts:
        raise GateError("E_POLICY_RECEIPTS", "receipt_log may not contain '..'")
    allow_create = gate.get("allow_create", False)
    if not isinstance(allow_create, bool):
        raise GateError("E_POLICY_VALUE", "gate.allow_create must be a boolean")

    raw_zones = data.get("zones")
    if not isinstance(raw_zones, list) or not raw_zones:
        raise GateError("E_POLICY_ZONES", "at least one [[zones]] entry is required")
    zones: list[Zone] = []
    names: set[str] = set()
    for raw_zone in raw_zones:
        if not isinstance(raw_zone, dict):
            raise GateError("E_POLICY_ZONES", "each zone must be a TOML table")
        unknown_zone = sorted(set(raw_zone) - {"name", "mode", "patterns", "extensions"})
        if unknown_zone:
            raise GateError("E_POLICY_KEY", f"unknown zone keys: {unknown_zone}")
        name = raw_zone.get("name")
        mode = raw_zone.get("mode")
        patterns = raw_zone.get("patterns")
        extensions = raw_zone.get("extensions", [])
        if not isinstance(name, str) or not name or name in names:
            raise GateError("E_POLICY_ZONES", "zone names must be unique non-empty strings")
        if not isinstance(mode, str) or mode not in _MODES:
            raise GateError("E_POLICY_ZONES", f"zone {name!r} has invalid mode {mode!r}")
        if (
            not isinstance(patterns, list)
            or not patterns
            or not all(isinstance(item, str) for item in patterns)
        ):
            raise GateError("E_POLICY_ZONES", f"zone {name!r} needs string patterns")
        if not isinstance(extensions, list) or not all(
            isinstance(item, str) and item.startswith(".") and item == item.lower()
            for item in extensions
        ):
            raise GateError("E_POLICY_ZONES", f"zone {name!r} has invalid extensions")
        names.add(name)
        pattern_values = tuple(patterns)
        zones.append(
            Zone(
                name=name,
                mode=mode,
                patterns=pattern_values,
                extensions=tuple(extensions),
                _compiled=tuple(_compile_pattern(item) for item in pattern_values),
            )
        )
    policy = Policy(
        source=source,
        root=root,
        receipt_log=receipt_log,
        max_bytes=_integer(gate, "max_bytes", 262_144),
        max_changed_bytes=_integer(gate, "max_changed_bytes", 65_536),
        allow_create=allow_create,
        zones=tuple(zones),
        sha256=sha256(raw),
    )
    authority_paths = [receipt_log]
    try:
        source.relative_to(root)
    except ValueError:
        pass
    else:
        authority_paths.append(source)
    for authority_path in authority_paths:
        relative = authority_path.relative_to(root).as_posix()
        matches = [zone for zone in policy.zones if zone.matches(relative)]
        if any(zone.mode == "mutable" for zone in matches) and not any(
            zone.mode != "mutable" for zone in matches
        ):
            raise GateError(
                "E_POLICY_AUTHORITY",
                f"authority path must not be mutable: {relative}",
            )
    return policy


def classify(policy: Policy, relative: str) -> Zone:
    """Return the mutable zone; any protected/immutable match wins."""

    matches = [zone for zone in policy.zones if zone.matches(relative)]
    denied = next((zone for zone in matches if zone.mode != "mutable"), None)
    if denied is not None:
        raise GateError("E_ZONE_DENIED", f"{relative} is {denied.mode} by zone {denied.name}")
    mutable = next((zone for zone in matches if zone.mode == "mutable"), None)
    if mutable is None:
        raise GateError("E_ZONE_UNMATCHED", f"{relative} is not in a mutable zone")
    suffix = PurePosixPath(relative).suffix.lower()
    if mutable.extensions and suffix not in mutable.extensions:
        raise GateError(
            "E_EXTENSION", f"extension {suffix or '<none>'} is denied by zone {mutable.name}"
        )
    return mutable


def _reject_symlink_components(root: Path, relative: PurePosixPath) -> None:
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        try:
            metadata = cursor.lstat()
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise GateError("E_PATH_STAT", f"cannot inspect {cursor}: {exc}") from exc
        if stat.S_ISLNK(metadata.st_mode):
            raise GateError("E_SYMLINK", f"symlink path component is forbidden: {cursor}")


def resolve_target(policy: Policy, raw: str) -> Target:
    """Resolve a target without following any target-path symlink."""

    if not raw or "\x00" in raw:
        raise GateError("E_PATH", "target path is empty or contains NUL")
    candidate = Path(raw)
    if ".." in candidate.parts:
        raise GateError("E_TRAVERSAL", "target path may not contain '..'")
    absolute = candidate if candidate.is_absolute() else policy.root / candidate
    normalized = Path(os.path.normpath(absolute))
    try:
        relative_path = normalized.relative_to(policy.root)
    except ValueError as exc:
        raise GateError("E_OUTSIDE_ROOT", "target is outside the policy root") from exc
    if not relative_path.parts:
        raise GateError("E_PATH", "policy root itself cannot be a target")
    relative = PurePosixPath(*relative_path.parts).as_posix()
    _reject_symlink_components(policy.root, PurePosixPath(relative))
    zone = classify(policy, relative)
    parent = normalized.parent
    if not parent.is_dir():
        raise GateError("E_PARENT", f"target parent does not exist: {parent}")
    return Target(path=normalized, relative=relative, zone=zone)
