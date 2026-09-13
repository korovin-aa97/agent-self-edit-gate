from __future__ import annotations

import re
from pathlib import Path

REPOSITORY = Path(__file__).parents[1]
EXAMPLE = REPOSITORY / "examples/protected-ci/verify-receipts.yml"


def test_protected_ci_example_keeps_the_trust_boundary_explicit() -> None:
    workflow = EXAMPLE.read_text(encoding="utf-8")

    assert "pull_request_target:" in workflow
    assert "permissions:\n  contents: read\n" in workflow
    assert "persist-credentials: false" in workflow
    assert "agent-self-edit-gate==0.1.3" in workflow
    assert "selfedit-gate --policy selfedit-policy.toml verify-receipts" in workflow
    assert "--no-current-files" not in workflow

    action_pins = re.findall(r"uses: [^@\s]+@([^\s]+)", workflow)
    assert action_pins
    assert all(re.fullmatch(r"[0-9a-f]{40}", pin) for pin in action_pins)
