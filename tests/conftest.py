from __future__ import annotations

from pathlib import Path

import pytest

from selfedit_gate.policy import Policy, load_policy


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    (tmp_path / "agents").mkdir()
    (tmp_path / "agents" / "reviewer.md").write_text("old\n", encoding="utf-8")
    (tmp_path / "protected").mkdir()
    (tmp_path / "protected" / "settings.md").write_text("secret\n", encoding="utf-8")
    return tmp_path


def write_policy(
    root: Path,
    *,
    allow_create: bool = False,
    max_bytes: int = 1024,
    max_changed_bytes: int = 256,
    extra_zones: str = "",
    receipt_log: str = ".selfedit-gate/receipts.jsonl",
) -> Path:
    path = root / "selfedit-policy.toml"
    path.write_text(
        f"""schema_version = 1

[gate]
root = "."
receipt_log = "{receipt_log}"
max_bytes = {max_bytes}
max_changed_bytes = {max_changed_bytes}
allow_create = {str(allow_create).lower()}

[[zones]]
name = "behaviour"
mode = "mutable"
patterns = ["agents/**/*", "protected/*.md"]
extensions = [".md"]

[[zones]]
name = "authority"
mode = "immutable"
patterns = ["selfedit-policy.toml", ".selfedit-gate/**", "protected/**"]
{extra_zones}
""",
        encoding="utf-8",
    )
    return path


@pytest.fixture
def policy(repository: Path) -> Policy:
    return load_policy(write_policy(repository))
