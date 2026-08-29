from __future__ import annotations

import os
from pathlib import Path

import pytest

from selfedit_gate.errors import GateError
from selfedit_gate.policy import classify, load_policy, resolve_target

from .conftest import write_policy


def assert_code(expected: str, callable_: object) -> None:
    with pytest.raises(GateError) as captured:
        callable_()  # type: ignore[operator]
    assert captured.value.code == expected


def test_mutable_nested_glob_and_deny_overlap(repository: Path) -> None:
    policy = load_policy(write_policy(repository))
    target = resolve_target(policy, "agents/reviewer.md")
    assert target.zone.name == "behaviour"
    assert_code("E_ZONE_DENIED", lambda: classify(policy, "protected/settings.md"))


def test_refuses_traversal_and_absolute_escape(repository: Path) -> None:
    policy = load_policy(write_policy(repository))
    assert_code("E_TRAVERSAL", lambda: resolve_target(policy, "agents/../agents/reviewer.md"))
    assert_code("E_OUTSIDE_ROOT", lambda: resolve_target(policy, "/tmp/reviewer.md"))


def test_refuses_symlink_file_and_parent(repository: Path) -> None:
    policy = load_policy(write_policy(repository))
    (repository / "agents" / "link.md").symlink_to(repository / "agents" / "reviewer.md")
    assert_code("E_SYMLINK", lambda: resolve_target(policy, "agents/link.md"))
    (repository / "linked").symlink_to(repository / "agents", target_is_directory=True)
    amended = write_policy(
        repository,
        extra_zones="""
[[zones]]
name = "linked"
mode = "mutable"
patterns = ["linked/*.md"]
extensions = [".md"]
""",
    )
    assert_code("E_SYMLINK", lambda: resolve_target(load_policy(amended), "linked/reviewer.md"))


def test_refuses_extension_case_and_unmatched(repository: Path) -> None:
    policy = load_policy(write_policy(repository))
    assert_code("E_EXTENSION", lambda: classify(policy, "agents/config.toml"))
    assert_code("E_ZONE_UNMATCHED", lambda: classify(policy, "README.md"))


def test_unknown_policy_keys_and_versions_fail(repository: Path) -> None:
    path = write_policy(repository)
    path.write_text(path.read_text().replace("schema_version = 1", "schema_version = 2"))
    assert_code("E_POLICY_VERSION", lambda: load_policy(path))
    path = write_policy(repository)
    path.write_text(path.read_text().replace("allow_create = false", "mystery = true"))
    assert_code("E_POLICY_KEY", lambda: load_policy(path))


@pytest.mark.parametrize("invalid_version", ["true", "1.0"])
def test_policy_version_requires_an_integer(repository: Path, invalid_version: str) -> None:
    path = write_policy(repository)
    path.write_text(
        path.read_text().replace("schema_version = 1", f"schema_version = {invalid_version}")
    )
    assert_code("E_POLICY_VERSION", lambda: load_policy(path))


def test_invalid_zone_mode_is_a_policy_error(repository: Path) -> None:
    path = write_policy(repository)
    path.write_text(path.read_text().replace('mode = "mutable"', 'mode = ["mutable"]'))
    assert_code("E_POLICY_ZONES", lambda: load_policy(path))


def test_receipt_path_must_stay_inside_root(repository: Path) -> None:
    path = write_policy(repository, receipt_log="../outside.jsonl")
    assert_code("E_POLICY_RECEIPTS", lambda: load_policy(path))


@pytest.mark.parametrize("receipt_log", ["", "."])
def test_receipt_path_must_name_a_file(repository: Path, receipt_log: str) -> None:
    path = write_policy(repository, receipt_log=receipt_log)
    assert_code("E_POLICY_RECEIPTS", lambda: load_policy(path))


def test_policy_and_receipt_authority_cannot_be_mutable(repository: Path) -> None:
    path = write_policy(
        repository,
        receipt_log="agents/receipts.md",
        extra_zones="""
[[zones]]
name = "policy-mutable"
mode = "mutable"
patterns = ["selfedit-policy.toml"]
extensions = [".toml"]
""",
    )
    assert_code("E_POLICY_AUTHORITY", lambda: load_policy(path))


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlinks unavailable")
def test_broken_symlink_is_refused(repository: Path) -> None:
    policy = load_policy(write_policy(repository))
    (repository / "agents" / "broken.md").symlink_to(repository / "missing.md")
    assert_code("E_SYMLINK", lambda: resolve_target(policy, "agents/broken.md"))
