# Receipt protocol (schema v1)

Each accepted mutation produces two canonical JSON Lines records:

1. `intent`, durably appended before the target changes;
2. `commit`, durably appended after the atomic replacement.

Records contain `schema_version`, monotonic `sequence`, UTC `timestamp`, random
`operation_id`, action, repository-relative path, zone, exact policy hash,
before/proposed-after hashes, byte bounds, and the prior record hash. A commit
also contains `after_sha256`.

`record_sha256` is SHA-256 over the UTF-8 canonical JSON object with that one
field removed: ASCII escaped, sorted keys, and compact separators. The first
record uses 64 zeroes for `previous_record_sha256`.

```bash
selfedit-gate --policy selfedit-policy.toml verify-receipts
selfedit-gate --json --policy selfedit-policy.toml verify-receipts
```

The verifier checks JSON framing, sequence and record chains, intent/commit
pairing, the current policy hash, per-file before/after continuity, and the
current hash of every last-touched file. `--no-current-files` verifies only the
journal; use it for archived repositories, not as an enforcement substitute.

## What a receipt proves

A valid independently anchored chain shows that these bytes are consistent
with operations accepted under a policy with this exact hash. It does not prove
who requested the change, that the new prompt is benign, or that alternate
filesystem writes were impossible.

Keep the journal and policy protected from the agent. In CI, pin the package
version, run the verifier from a protected workflow, and store the resulting
head hash or artifact somewhere the agent cannot rewrite.

The gateway refuses non-regular or hard-linked journals and any nested receipt
directory that is not owned by the gateway user or is group/world writable.
These checks prevent a writable audit directory or an outside hard link from
redirecting append operations. They do not replace an independent receipt-head
anchor or OS access control.

## Incomplete operations

A dangling intent is always an error. It can mean a crash, forced termination,
write failure, or deliberate interference. v0.1 does not auto-repair it because
choosing the intended or prior content is a human authorization decision.
