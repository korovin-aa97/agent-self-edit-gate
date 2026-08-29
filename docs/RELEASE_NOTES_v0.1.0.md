# Agent Self-Edit Gate v0.1.0

Agent Self-Edit Gate is a narrow, deterministic write gateway for coding agents
that improve their own prompts, skills, and agent definitions.

## Why it exists

Behaviour files frequently sit next to authority files. A useful agent may
update a review skill, but it should not use the same self-edit workflow to
rewrite permissions, hooks, CI, or the policy enforcing that distinction.

## Included in v0.1.0

- TOML policy schema v1 with deny-before-allow zones.
- `check`, exact `replace`, bounded whole-file `write`, and
  `verify-receipts` commands.
- UTF-8, extension, size, changed-byte, traversal, symlink, owner, file-type,
  target-race, and policy-swap refusals.
- Local-filesystem atomic replacement on Linux and macOS.
- Hash-chained intent/commit receipt schema v1 with dangling-intent detection.
- Stable JSON errors, typed Python package, zero runtime dependencies, profiles,
  threat model, deployment recipes, CI, and hostile/crash tests.

## The important limitation

This CLI cannot stop an agent that can write around it. Enforcement requires an
external sandbox, OS policy, protected broker, or protected CI boundary. The
receipts are tamper-evident, not signed, and v0.1 has not received an independent
professional security audit.

Read [the threat model](https://github.com/korovin-aa97/agent-self-edit-gate/blob/v0.1.0/docs/THREAT_MODEL.md)
before deployment.

## Install

Download the wheel attached to this release, then:

```bash
python -m pip install agent_self_edit_gate-0.1.0-py3-none-any.whl
selfedit-gate --version
```

Python 3.12+ on Linux and macOS is supported. This version was subsequently
published through OIDC trusted publishing at
[PyPI](https://pypi.org/project/agent-self-edit-gate/0.1.0/); no long-lived
publishing token is stored in the repository.
