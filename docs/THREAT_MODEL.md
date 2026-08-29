# Threat model

This document defines the security claim for Agent Self-Edit Gate v0.1.0. It is
part of the product contract, not a marketing appendix.

## Security claim

When an external sandbox or filesystem policy makes `selfedit-gate` the only
writer available to an agent, the gate permits bounded UTF-8 changes only in
policy-declared mutable paths, refuses protected and immutable paths, and
records each accepted mutation in a verifiable intent/commit hash chain.

Without that external writer restriction, the CLI is a convention and audit
aid. An agent with unrestricted shell, editor, Python, Git, or direct filesystem
write access can bypass it.

## Assets

- Authority files: permissions, hooks, credentials, sandbox settings, CI,
  CODEOWNERS, and the gate policy itself.
- Behaviour files: prompts, skills, agent definitions, and shared instructions.
- Receipt integrity: the order, policy hash, before hash, and after hash for
  each accepted write.
- Repository availability and the integrity of unrelated files.

## Actors and capabilities

The untrusted actor is a coding agent processing possibly hostile repository or
tool output. It may choose any CLI arguments and file contents, repeat requests,
race files it is allowed to access, and terminate the gate process.

The trusted operator chooses the policy and external enforcement boundary. The
operator may deliberately update policy or rotate a receipt journal, but those
actions happen outside this gate and must use ordinary human review.

The verifier is trusted only when it runs from protected CI, a separate
read-only account, or another environment the editing agent cannot rewrite. A
receipt check run by the same unrestricted agent is useful diagnostics, not
independent evidence.

## Trust anchors

At least one external mechanism must deny alternate writes. Examples include a
container with behaviour files writable only through a small broker, OS ACLs
with a separately privileged gateway process, or protected CI that accepts only
patches accompanied by valid receipts and replays policy checks. The policy,
receipt journal, verifier binary/environment, and CI definition must be outside
the editing agent's write authority.

## Addressed threats

| Threat | v0.1 response |
| --- | --- |
| Path traversal or absolute escape | lexical containment and explicit `..` refusal |
| Symlink file or parent | every existing target component is checked; final opens use `O_NOFOLLOW` |
| Protected/mutable overlap | protected or immutable always wins |
| Unsupported or binary content | extension allowlist, UTF-8 requirement, NUL refusal |
| Resource exhaustion | bounded input, file, changed-byte, and journal sizes |
| Ambiguous edit | exact replacement anchor must occur once |
| Target race | parent directory descriptor plus inode/device/owner re-check before replace |
| Partial target write | same-directory temporary file, `fsync`, atomic replace, directory `fsync` |
| Policy swap | exact policy bytes are hashed and re-read before the mutation |
| Receipt tampering/truncation | ordered SHA-256 record chain and strict final-newline parsing |
| Crash before write | an intent may remain; verification reports a dangling intent |
| Crash after replace/before commit | current hash plus dangling intent exposes incomplete protocol |
| Audit path failure | owned, non-group/world-writable journal and durable intent before mutation |
| Concurrent gate writers | exclusive advisory journal lock serializes gate operations |

`protected` and `immutable` have identical deny behaviour in v0.1. Their names
communicate ownership: protected files may be changed by a reviewed external
workflow, while immutable files are expected never to be changed by agents.

## Known bypasses and non-goals

- The gate does not stop direct writes outside the CLI.
- It is not a shell sandbox, agent firewall, malware scanner, prompt-injection
  detector, access-control server, or approval workflow.
- Receipts are tamper-evident, not signed. Anyone who can replace the complete
  journal and the independent anchor can forge history.
- The gate does not authenticate an agent or person.
- It does not protect confidentiality or prevent a permitted prompt edit from
  containing malicious instructions.
- It does not merge edits, interpret TOML/Markdown meaning, or ask an LLM to
  make a policy decision.
- Network filesystems may weaken `fsync`, locking, inode, or atomic-replace
  assumptions. v0.1 supports local filesystems on Linux and macOS only.
- A privileged local process can defeat user-level ownership and path checks.

## Crash protocol

The gate locks the journal, reads and hashes the target, writes and fsyncs an
`intent`, rechecks policy and target identity, atomically replaces the target,
then writes and fsyncs a `commit`. A verifier treats every dangling intent as a
failure. Recovery is deliberately manual in v0.1: inspect the target and intent,
restore or approve the file through an independent workflow, then rotate or
repair the journal with a documented human decision.

## Residual risks

The final path-component checks and directory-descriptor write reduce common
TOCTOU attacks, but this package has not received an independent professional
security audit. Treat v0.1 as an alpha security control and layer it with OS
isolation, protected review, least privilege, backups, and normal Git history.

Report vulnerabilities privately as described in [SECURITY.md](../SECURITY.md).
