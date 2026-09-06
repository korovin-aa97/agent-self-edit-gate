# Agent Self-Edit Gate v0.1.2

v0.1.2 is a security-documentation and evaluation-path patch for the public
alpha. It does not change policy schema v1, receipt schema v1, or CLI behavior.

## Security boundary clarification

- The README now says plainly that the CLI is not a sandbox and can be bypassed
  when an agent retains unrestricted shell or filesystem write access.
- The protected-CI deployment model now requires the accepted receipt head or
  journal to be anchored outside the agent's write authority. Verifying only a
  replacement journal supplied by that same agent is diagnostics, not
  independent evidence.
- The deployment table now qualifies its merge-time security boundary: the
  agent must be unable to rewrite the anchors, verifier, or required checks.
- Receipt wording now accurately describes stored hashes rather than implying
  that complete before/proposed file contents are embedded in each record.

## Release integrity

- The source-distribution configuration explicitly excludes the internal
  launch kit, keeping campaign planning out of published packages even when it
  exists in a maintainer worktree.

## Evaluation and documentation

- A structured GitHub issue form collects the proposed writer boundary and
  requires reporters to remove credentials and private repository details.
- A deterministic terminal cast runs the real CLI through an allowed edit, a
  denied authority path, and receipt verification.
- Reproducible launch cards and asset-regeneration instructions keep the
  `NOT A SANDBOX` limitation visible in shared visuals.

## Install

```bash
python -m pip install "agent-self-edit-gate==0.1.2"
selfedit-gate --version
```

Python 3.12+ on local Linux and macOS filesystems is supported. Agent Self-Edit
Gate has not received an independent professional security audit.
