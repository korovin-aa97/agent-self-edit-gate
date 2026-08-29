"""Command-line interface for Agent Self-Edit Gate."""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .errors import GateError
from .gate import check, exact_replace, guarded_write, verify_receipts
from .policy import load_policy


def _bounded_read(path: Path, limit: int, *, label: str) -> bytes:
    try:
        if str(path) == "-":
            data = sys.stdin.buffer.read(limit + 1)
        else:
            descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
            with os.fdopen(descriptor, "rb") as stream:
                if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                    raise GateError("E_INPUT_TYPE", f"{label} must be a regular file")
                data = stream.read(limit + 1)
    except OSError as exc:
        raise GateError("E_INPUT_READ", f"cannot read {label}: {exc}") from exc
    if len(data) > limit:
        raise GateError("E_INPUT_SIZE", f"{label} exceeds {limit} bytes")
    return data


def _emit(payload: dict[str, Any], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, sort_keys=True))
    elif payload.get("ok"):
        result = payload.get("result", {})
        if "valid" in result:
            print(f"valid: {result['operations']} operations, {result['records']} records")
        elif "mutable" in result:
            print(f"mutable: {result['path']} ({result['zone']})")
        else:
            print(f"updated: {result['path']} ({result['operation_id']})")
    else:
        error = payload["error"]
        print(f"selfedit-gate: {error['code']}: {error['message']}", file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="selfedit-gate",
        description="Policy-enforced writes for coding-agent behaviour files.",
    )
    parser.add_argument("--policy", type=Path, default=Path("selfedit-policy.toml"))
    parser.add_argument("--json", action="store_true", help="emit stable JSON")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_parser = subparsers.add_parser("check", help="classify a target path")
    check_parser.add_argument("target")

    replace_parser = subparsers.add_parser(
        "replace", help="replace one exact byte sequence in an existing file"
    )
    replace_parser.add_argument("target")
    replace_parser.add_argument("old_file", type=Path)
    replace_parser.add_argument("new_file", type=Path)

    write_parser = subparsers.add_parser(
        "write", help="write a complete UTF-8 file through the policy gate"
    )
    write_parser.add_argument("target")
    write_parser.add_argument("content_file", type=Path, help="file path, or - for stdin")

    verify_parser = subparsers.add_parser(
        "verify-receipts", help="verify the receipt and current-file hash chains"
    )
    verify_parser.add_argument(
        "--no-current-files",
        action="store_true",
        help="verify the journal only, without comparing current files",
    )
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    policy = load_policy(args.policy)
    if args.command == "check":
        return check(policy, args.target)
    if args.command == "replace":
        old = _bounded_read(args.old_file, policy.max_bytes, label="old anchor")
        new = _bounded_read(args.new_file, policy.max_bytes, label="replacement")
        return exact_replace(policy, args.target, old, new)
    if args.command == "write":
        content = _bounded_read(args.content_file, policy.max_bytes, label="content")
        return guarded_write(policy, args.target, content, action="write")
    if args.command == "verify-receipts":
        return verify_receipts(policy, check_files=not args.no_current_files)
    raise GateError("E_COMMAND", f"unknown command {args.command!r}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run(args)
    except GateError as exc:
        _emit(
            {"ok": False, "error": {"code": exc.code, "message": exc.message}},
            as_json=args.json,
        )
        return 2
    except (OSError, ValueError) as exc:
        _emit(
            {"ok": False, "error": {"code": "E_INTERNAL_IO", "message": str(exc)}},
            as_json=args.json,
        )
        return 2
    _emit({"ok": True, "result": result}, as_json=args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
