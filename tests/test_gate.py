from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from selfedit_gate.errors import GateError
from selfedit_gate.gate import exact_replace, guarded_write, verify_receipts
from selfedit_gate.policy import Policy, load_policy
from selfedit_gate.receipts import ReceiptJournal, parse_records

from .conftest import write_policy


def error_code(callable_: object) -> str:
    with pytest.raises(GateError) as captured:
        callable_()  # type: ignore[operator]
    return captured.value.code


def test_exact_replace_and_verify_receipts(policy: Policy) -> None:
    result = exact_replace(policy, "agents/reviewer.md", b"old", b"new")
    assert result["action"] == "replace"
    assert (policy.root / "agents/reviewer.md").read_text() == "new\n"
    verified = verify_receipts(policy)
    assert verified == {
        "valid": True,
        "records": 2,
        "operations": 1,
        "files": 1,
        "policy_sha256": policy.sha256,
        "current_files_checked": True,
    }
    records = parse_records(policy.receipt_log.read_bytes())
    assert [record["phase"] for record in records] == ["intent", "commit"]


def test_empty_receipt_journal_verifies(policy: Policy) -> None:
    assert verify_receipts(policy)["records"] == 0


def test_write_preserves_mode(policy: Policy) -> None:
    target = policy.root / "agents/reviewer.md"
    target.chmod(0o640)
    guarded_write(policy, "agents/reviewer.md", b"replacement\n", action="write")
    assert target.stat().st_mode & 0o777 == 0o640


def test_create_policy(policy: Policy, repository: Path) -> None:
    assert (
        error_code(lambda: guarded_write(policy, "agents/new.md", b"new\n", action="write"))
        == "E_CREATE_DENIED"
    )
    creation_policy = load_policy(write_policy(repository, allow_create=True))
    guarded_write(creation_policy, "agents/new.md", b"new\n", action="write")
    assert (repository / "agents/new.md").stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (b"x\x00y", "E_BINARY"),
        (b"\xff", "E_ENCODING"),
        (b"x" * 1025, "E_SIZE"),
    ],
)
def test_refuses_binary_encoding_and_size(policy: Policy, content: bytes, expected: str) -> None:
    assert (
        error_code(lambda: guarded_write(policy, "agents/reviewer.md", content, action="write"))
        == expected
    )


def test_refuses_oversized_change(repository: Path) -> None:
    policy = load_policy(write_policy(repository, max_changed_bytes=2))
    assert (
        error_code(
            lambda: guarded_write(policy, "agents/reviewer.md", b"entirely new\n", action="write")
        )
        == "E_DIFF_SIZE"
    )


def test_anchor_must_be_exactly_once(policy: Policy) -> None:
    assert (
        error_code(lambda: exact_replace(policy, "agents/reviewer.md", b"", b"new"))
        == "E_EMPTY_ANCHOR"
    )
    assert (
        error_code(lambda: exact_replace(policy, "agents/reviewer.md", b"missing", b"new"))
        == "E_ANCHOR_COUNT"
    )
    target = policy.root / "agents/reviewer.md"
    target.write_text("old old")
    assert (
        error_code(lambda: exact_replace(policy, "agents/reviewer.md", b"old", b"new"))
        == "E_ANCHOR_COUNT"
    )


def test_audit_failure_occurs_before_target_write(repository: Path) -> None:
    (repository / ".selfedit-gate").write_text("not a directory")
    policy = load_policy(write_policy(repository))
    original = (repository / "agents/reviewer.md").read_bytes()
    assert (
        error_code(lambda: guarded_write(policy, "agents/reviewer.md", b"new\n", action="write"))
        == "E_AUDIT_PATH"
    )
    assert (repository / "agents/reviewer.md").read_bytes() == original


def test_interrupted_atomic_write_keeps_original_and_leaves_intent(
    policy: Policy, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_replace(*args: object, **kwargs: object) -> None:
        raise OSError("simulated crash point")

    monkeypatch.setattr(os, "replace", fail_replace)
    original = (policy.root / "agents/reviewer.md").read_bytes()
    assert (
        error_code(lambda: guarded_write(policy, "agents/reviewer.md", b"new\n", action="write"))
        == "E_ATOMIC_WRITE"
    )
    assert (policy.root / "agents/reviewer.md").read_bytes() == original
    assert error_code(lambda: verify_receipts(policy)) == "E_DANGLING_INTENT"


def test_target_race_after_intent_is_refused(
    policy: Policy, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_append = ReceiptJournal.append
    target = policy.root / "agents/reviewer.md"

    def append_and_race(journal: ReceiptJournal, fields: dict[str, object]) -> dict[str, object]:
        record = original_append(journal, fields)
        if fields["phase"] == "intent":
            target.unlink()
            target.write_text("racer\n")
        return record

    monkeypatch.setattr(ReceiptJournal, "append", append_and_race)
    assert (
        error_code(lambda: guarded_write(policy, "agents/reviewer.md", b"new\n", action="write"))
        == "E_TARGET_RACE"
    )
    assert target.read_text() == "racer\n"


def test_policy_swap_after_intent_is_refused(
    policy: Policy, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = 0
    original = Policy.assert_unchanged

    def swap_on_second_check(active_policy: Policy) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            active_policy.source.write_text(active_policy.source.read_text() + "\n# swap\n")
        original(active_policy)

    monkeypatch.setattr(Policy, "assert_unchanged", swap_on_second_check)
    before = (policy.root / "agents/reviewer.md").read_bytes()
    assert (
        error_code(lambda: guarded_write(policy, "agents/reviewer.md", b"new\n", action="write"))
        == "E_POLICY_CHANGED"
    )
    assert (policy.root / "agents/reviewer.md").read_bytes() == before


def test_commit_receipt_failure_is_detectable(
    policy: Policy, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_append = ReceiptJournal.append
    calls = 0

    def fail_commit(journal: ReceiptJournal, fields: dict[str, object]) -> dict[str, object]:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise GateError("E_AUDIT_WRITE", "simulated commit failure")
        return original_append(journal, fields)

    monkeypatch.setattr(ReceiptJournal, "append", fail_commit)
    assert (
        error_code(lambda: guarded_write(policy, "agents/reviewer.md", b"new\n", action="write"))
        == "E_AUDIT_WRITE"
    )
    assert (policy.root / "agents/reviewer.md").read_bytes() == b"new\n"
    assert error_code(lambda: verify_receipts(policy)) == "E_DANGLING_INTENT"


def test_manual_dangling_intent_is_rejected(policy: Policy) -> None:
    with ReceiptJournal(policy) as journal:
        journal.append(
            {
                "operation_id": "f" * 32,
                "phase": "intent",
                "action": "write",
                "path": "agents/reviewer.md",
                "zone": "behaviour",
                "policy_sha256": policy.sha256,
                "before_sha256": "0" * 64,
                "proposed_after_sha256": "1" * 64,
                "content_bytes": 1,
                "changed_bytes": 1,
            }
        )
    assert error_code(lambda: verify_receipts(policy)) == "E_DANGLING_INTENT"


def test_receipt_truncation_and_tampering_are_rejected(policy: Policy) -> None:
    exact_replace(policy, "agents/reviewer.md", b"old", b"new")
    raw = policy.receipt_log.read_bytes()
    policy.receipt_log.write_bytes(raw[:-1])
    assert error_code(lambda: verify_receipts(policy)) == "E_AUDIT_TRUNCATED"
    policy.receipt_log.write_bytes(raw.replace(b'"action":"replace"', b'"action":"rewrite"', 1))
    assert error_code(lambda: verify_receipts(policy)) == "E_RECEIPT_FIELDS"


def test_group_writable_receipt_journal_is_rejected(policy: Policy) -> None:
    exact_replace(policy, "agents/reviewer.md", b"old", b"new")
    policy.receipt_log.chmod(0o660)
    assert error_code(lambda: verify_receipts(policy)) == "E_AUDIT_MODE"


def test_current_file_bypass_is_detected(policy: Policy) -> None:
    exact_replace(policy, "agents/reviewer.md", b"old", b"new")
    (policy.root / "agents/reviewer.md").write_text("bypass\n")
    assert error_code(lambda: verify_receipts(policy)) == "E_CURRENT_HASH"


def test_policy_swap_is_detected(policy: Policy) -> None:
    exact_replace(policy, "agents/reviewer.md", b"old", b"new")
    policy.source.write_text(policy.source.read_text() + "\n# changed\n")
    assert error_code(lambda: verify_receipts(policy)) == "E_POLICY_CHANGED"


def test_receipt_pair_field_change_is_detected(policy: Policy) -> None:
    exact_replace(policy, "agents/reviewer.md", b"old", b"new")
    lines = [json.loads(line) for line in policy.receipt_log.read_text().splitlines()]
    assert lines[0]["operation_id"] == lines[1]["operation_id"]


def test_receipt_schema_rejects_duplicate_and_invalid_fields(policy: Policy) -> None:
    exact_replace(policy, "agents/reviewer.md", b"old", b"new")
    valid_line = policy.receipt_log.read_text().splitlines()[0]
    duplicate = valid_line.replace('{"action":', '{"sequence":1,"action":', 1)
    policy.receipt_log.write_text(duplicate + "\n")
    assert error_code(lambda: verify_receipts(policy)) == "E_AUDIT_JSON"

    record = json.loads(valid_line)
    record["timestamp"] = "not-a-time"
    policy.receipt_log.write_text(json.dumps(record) + "\n")
    assert error_code(lambda: verify_receipts(policy)) == "E_RECEIPT_FIELDS"

    record = json.loads(valid_line)
    record["content_bytes"] = True
    policy.receipt_log.write_text(json.dumps(record) + "\n")
    assert error_code(lambda: verify_receipts(policy)) == "E_RECEIPT_FIELDS"

    record = json.loads(valid_line)
    record["operation_id"] = "short"
    policy.receipt_log.write_text(json.dumps(record) + "\n")
    assert error_code(lambda: verify_receipts(policy)) == "E_RECEIPT_FIELDS"
