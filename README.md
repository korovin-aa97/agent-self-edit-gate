# Agent Self-Edit Gate

Private draft extracted from the policy-enforced self-edit boundary used in a
mixed Claude/Codex production fleet.

The gate lets an agent update behaviour files such as prompts, skills, and
agent definitions while refusing changes to the files that grant permissions,
install hooks, or define enforcement policy.

## Draft scope

- repository-relative path policy with `mutable`, `protected`, and `immutable`
  zones;
- deny-before-allow evaluation and real-path containment;
- exact, single-anchor replacements;
- atomic writes with intent/commit receipts;
- no LLM, network service, or fleet orchestration.

This is an untested extraction draft, not a security boundary yet. A shell or
tool that can write around this CLI can also bypass it. Before any public
release the repository needs a threat model and an independent enforcement
story such as a sandbox or protected CI policy.

## Sketch

```bash
selfedit-gate check --policy selfedit-policy.toml .claude/agents/reviewer.md
selfedit-gate replace --policy selfedit-policy.toml \
  .claude/agents/reviewer.md old.txt new.txt
```

No public license has been selected while this repository is private.
