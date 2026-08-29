from __future__ import annotations

import json
import os
import subprocess
import sys
from io import BytesIO, TextIOWrapper
from pathlib import Path

import pytest

from selfedit_gate.cli import main

from .conftest import write_policy


def run_cli(repository: Path, *args: str) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")
    return subprocess.run(
        [sys.executable, "-m", "selfedit_gate.cli", *args],
        cwd=repository,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )


def test_json_check_and_stable_error(repository: Path) -> None:
    write_policy(repository)
    allowed = run_cli(repository, "--json", "check", "agents/reviewer.md")
    assert allowed.returncode == 0
    assert json.loads(allowed.stdout)["result"]["mutable"] is True
    denied = run_cli(repository, "--json", "check", "protected/settings.md")
    assert denied.returncode == 2
    assert json.loads(denied.stdout)["error"]["code"] == "E_ZONE_DENIED"


def test_cli_write_replace_and_verify(repository: Path) -> None:
    write_policy(repository)
    content = repository / "content.md"
    content.write_text("first\n")
    written = run_cli(repository, "write", "agents/reviewer.md", str(content))
    assert written.returncode == 0, written.stderr
    old = repository / "old.txt"
    new = repository / "new.txt"
    old.write_text("first")
    new.write_text("second")
    replaced = run_cli(
        repository,
        "replace",
        "agents/reviewer.md",
        str(old),
        str(new),
    )
    assert replaced.returncode == 0, replaced.stderr
    verified = run_cli(repository, "verify-receipts")
    assert verified.returncode == 0, verified.stderr
    assert "valid: 2 operations, 4 records" in verified.stdout


def test_direct_cli_json_write_replace_verify_and_errors(
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    write_policy(repository)
    monkeypatch.chdir(repository)
    assert main(["check", "agents/reviewer.md"]) == 0
    assert "mutable:" in capsys.readouterr().out
    content = repository / "content.md"
    content.write_text("first\n")
    assert main(["--json", "write", "agents/reviewer.md", str(content)]) == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True

    old = repository / "old.txt"
    new = repository / "new.txt"
    old.write_text("first")
    new.write_text("second")
    assert main(["replace", "agents/reviewer.md", str(old), str(new)]) == 0
    assert "updated:" in capsys.readouterr().out
    assert main(["verify-receipts", "--no-current-files"]) == 0
    assert "valid:" in capsys.readouterr().out
    assert main(["check", "protected/settings.md"]) == 2
    assert "E_ZONE_DENIED" in capsys.readouterr().err


def test_direct_cli_stdin_and_input_failures(
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    write_policy(repository)
    monkeypatch.chdir(repository)
    fake_stdin = TextIOWrapper(BytesIO(b"stdin content\n"), encoding="utf-8")
    monkeypatch.setattr(sys, "stdin", fake_stdin)
    assert main(["write", "agents/reviewer.md", "-"]) == 0
    capsys.readouterr()
    assert main(["write", "agents/reviewer.md", "missing-file"]) == 2
    assert "E_INPUT_READ" in capsys.readouterr().err

    oversized = repository / "oversized.md"
    oversized.write_bytes(b"x" * 1025)
    assert main(["--json", "write", "agents/reviewer.md", str(oversized)]) == 2
    assert json.loads(capsys.readouterr().out)["error"]["code"] == "E_INPUT_SIZE"


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFOs unavailable")
def test_cli_refuses_fifo_input(
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    write_policy(repository)
    fifo = repository / "content.fifo"
    os.mkfifo(fifo)
    monkeypatch.chdir(repository)
    assert main(["--json", "write", "agents/reviewer.md", str(fifo)]) == 2
    assert json.loads(capsys.readouterr().out)["error"]["code"] == "E_INPUT_TYPE"


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as captured:
        main(["--version"])
    assert captured.value.code == 0
    assert capsys.readouterr().out.strip() == "selfedit-gate 0.1.1"
