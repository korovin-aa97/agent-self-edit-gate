"""Generate a fixed-timing asciicast from real selfedit-gate subprocess output."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Step:
    command: str
    arguments: tuple[str, ...]
    expected_status: int
    expected_output: str


STEPS = (
    Step(
        command="selfedit-gate check .agents/reviewer.md",
        arguments=("check", ".agents/reviewer.md"),
        expected_status=0,
        expected_output="mutable: .agents/reviewer.md (shared-agent-behaviour)",
    ),
    Step(
        command="selfedit-gate replace .agents/reviewer.md old.txt new.txt",
        arguments=("replace", ".agents/reviewer.md", "old.txt", "new.txt"),
        expected_status=0,
        expected_output="updated: .agents/reviewer.md (<operation-id>)",
    ),
    Step(
        command="selfedit-gate check .github/workflows/ci.yml",
        arguments=("check", ".github/workflows/ci.yml"),
        expected_status=2,
        expected_output=(
            "selfedit-gate: E_ZONE_DENIED: .github/workflows/ci.yml is protected by zone "
            "repository-authority"
        ),
    ),
    Step(
        command="selfedit-gate verify-receipts",
        arguments=("verify-receipts",),
        expected_status=0,
        expected_output="valid: 1 operations, 2 records",
    ),
)

TIMES = ((0.8, 1.8), (3.6, 4.8), (6.8, 8.0), (10.4, 11.6))
OPERATION_ID = re.compile(r"\([0-9a-f]{32}\)")


def _assert_version() -> None:
    command = [sys.executable, "-m", "selfedit_gate.cli", "--version"]
    completed = subprocess.run(  # noqa: S603 - executable and arguments are fixed above.
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    output = (completed.stdout + completed.stderr).strip()
    if completed.returncode != 0 or output != "selfedit-gate 0.1.3":
        raise RuntimeError(f"demo requires selfedit-gate 0.1.3, got {output!r}")


def _run_step(root: Path, step: Step) -> str:
    command = [sys.executable, "-m", "selfedit_gate.cli", *step.arguments]
    completed = subprocess.run(  # noqa: S603 - executable and arguments are fixed above.
        command,
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    output = (completed.stdout + completed.stderr).strip()
    output = OPERATION_ID.sub("(<operation-id>)", output)
    if completed.returncode != step.expected_status:
        raise RuntimeError(
            f"{step.command!r} exited {completed.returncode}, expected {step.expected_status}: "
            f"{output!r}"
        )
    if output != step.expected_output:
        raise RuntimeError(
            f"{step.command!r} produced {output!r}, expected {step.expected_output!r}"
        )
    return output


def _cast_bytes(repository: Path) -> bytes:
    _assert_version()
    with tempfile.TemporaryDirectory(prefix="selfedit-demo-") as temporary:
        root = Path(temporary)
        (root / ".agents").mkdir()
        (root / ".agents/reviewer.md").write_text("Review code carefully.\n", encoding="utf-8")
        (root / "old.txt").write_text("Review code carefully.\n", encoding="utf-8")
        (root / "new.txt").write_text("Review code and cite evidence.\n", encoding="utf-8")
        shutil.copyfile(repository / "profiles/generic.toml", root / "selfedit-policy.toml")
        outputs = [_run_step(root, step) for step in STEPS]

    header = {
        "version": 2,
        "width": 96,
        "height": 18,
        "timestamp": 0,
        "title": "Agent Self-Edit Gate v0.1.3 — allowed, denied, verified",
        "env": {"SHELL": "sh", "TERM": "xterm-256color"},
    }
    events: list[list[object]] = [
        [
            0.0,
            "o",
            "\u001b[1;36mAgent Self-Edit Gate\u001b[0m  "
            "\u001b[2mreal v0.1.3 CLI output\u001b[0m\r\n\r\n",
        ]
    ]
    for step, output, (command_time, output_time) in zip(STEPS, outputs, TIMES, strict=True):
        events.append([command_time, "o", f"\u001b[1;32m$\u001b[0m {step.command}\r\n"])
        color = "31" if step.expected_status else "37"
        events.append([output_time, "o", f"\u001b[{color}m{output}\u001b[0m\r\n\r\n"])
    events.append(
        [
            14.2,
            "o",
            "\u001b[1;36mALLOW behaviour  ·  DENY authority  ·  VERIFY receipts\u001b[0m\r\n",
        ]
    )
    lines = [json.dumps(header, sort_keys=True, separators=(",", ":"))]
    lines.extend(json.dumps(event, separators=(",", ":")) for event in events)
    encoded = ("\n".join(lines) + "\n").encode()
    if str(repository).encode() in encoded or str(root).encode() in encoded:
        raise RuntimeError("cast unexpectedly contains a host path")
    return encoded


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/assets/demo.cast"),
        help="asciicast v2 path",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if the checked-in cast differs from a fresh real run",
    )
    arguments = parser.parse_args()
    repository = Path(__file__).resolve().parents[1]
    output = arguments.output if arguments.output.is_absolute() else repository / arguments.output
    rendered = _cast_bytes(repository)
    if arguments.check:
        if not output.is_file() or output.read_bytes() != rendered:
            raise RuntimeError(f"{output} is stale; regenerate it without --check")
        print(f"valid deterministic cast: {output.relative_to(repository)}")
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(rendered)
    print(f"wrote deterministic cast: {output.relative_to(repository)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
