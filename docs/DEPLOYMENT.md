# Deployment recipes

The CLI becomes an enforcement boundary only when the agent cannot write around
it. These recipes are patterns, not one-command production hardening.

## Local evaluation

Use a disposable Git repository. Copy a profile to `selfedit-policy.toml`, keep
normal Git backups, and ask the agent to invoke only `selfedit-gate`. This tests
workflow fit but provides no security boundary if the agent still has shell or
editor writes.

## Protected CI evidence

Protect the policy, `.github/workflows`, and receipt journal with CODEOWNERS and
branch protection. In a workflow whose definition cannot be changed by the
agent, install a pinned release and run:

```bash
python -m pip install "agent-self-edit-gate==0.1.1"
selfedit-gate --policy selfedit-policy.toml verify-receipts
```

Also review the actual Git diff. Receipt verification complements review; it
does not decide whether prompt content is safe.

## Filesystem broker

Run the coding agent as an unprivileged user with behaviour paths read-only.
Expose a narrow broker account/process that owns only those files and accepts
the four CLI operations. Keep policy, journal, broker binary, and socket
configuration owned by another account. Deny the agent `sudo`, alternate
mounts, Git index tricks, and direct broker-account credentials.

Accept proposed content as bounded stdin or broker-protocol bytes. Do not let an
untrusted caller choose arbitrary host paths for the broker to read; file-path
arguments inherit the broker account's read authority.

## Claude Code

Start with [`profiles/claude-code.toml`](../profiles/claude-code.toml). Anthropic
documents tool permissions and `PreToolUse` hooks, but a project-local hook is
not independent when the same agent can rewrite its settings. Prefer managed
settings or OS isolation for the trust anchor.

## Codex

Start with [`profiles/codex.toml`](../profiles/codex.toml). Configure Codex's
sandbox and approvals so behaviour-file writes cannot use a general shell or
editor path. Keep `config.toml`, policy, and CI outside the mutable set.

See the [threat model](THREAT_MODEL.md) before claiming enforcement.
