# Agent Self-Edit Gate v0.1.3

v0.1.3 turns the protected-CI deployment guidance into a small, copy-ready
GitHub Actions recipe.

## What changed

- Added `examples/protected-ci/verify-receipts.yml`, pinned to
  `agent-self-edit-gate==0.1.3` and immutable action SHAs.
- Limited the workflow token to read-only repository contents and disabled
  persisted checkout credentials.
- Kept current-file verification enabled, so the check covers both the receipt
  journal and the files produced by committed operations.
- Documented the required CODEOWNERS, branch-protection, and external journal
  anchor assumptions, plus the special care required by `pull_request_target`.
- Added automated checks for YAML syntax and security-critical recipe settings.

## Security boundary

The CLI is not a sandbox. The recipe is independent evidence only when the
agent cannot rewrite the workflow, policy, verifier pin, or accepted journal
anchor. It deliberately executes no code from the pull request and grants no
write permission.

## Install

```bash
python -m pip install "agent-self-edit-gate==0.1.3"
selfedit-gate --version
```

Policy schema v1, receipt schema v1, and CLI behavior are unchanged.
