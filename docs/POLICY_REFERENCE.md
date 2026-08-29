# Policy reference (schema v1)

Policies are TOML files with `schema_version = 1`, one `[gate]` table, and one
or more `[[zones]]` tables. Unknown keys and invalid values fail closed.

```toml
schema_version = 1

[gate]
root = "."
receipt_log = ".selfedit-gate/receipts.jsonl"
max_bytes = 262144
max_changed_bytes = 65536
allow_create = false

[[zones]]
name = "behaviour"
mode = "mutable"
patterns = ["AGENTS.md", ".agents/**/*.md"]
extensions = [".md"]
```

## Gate fields

| Field | Meaning |
| --- | --- |
| `root` | repository root, relative to the policy file unless absolute |
| `receipt_log` | append-only JSONL path; it must remain below `root` |
| `max_bytes` | maximum old and new file size |
| `max_changed_bytes` | removed bytes plus added bytes outside the common prefix/suffix |
| `allow_create` | whether a matching mutable path may be created; default is `false` |

All byte limits are positive integers. New parent directories are never created
for targets. A newly created target starts with mode `0600`; replacement keeps
the existing file mode and ownership.

## Zones and precedence

`mode` is one of `mutable`, `protected`, or `immutable`. A path must match at
least one mutable zone. If it also matches any protected or immutable zone, the
write is denied regardless of table order. This is the deny-before-allow rule.

`extensions` applies to mutable matches and is case-insensitive at evaluation.
An empty list permits any extension, although explicit lists are recommended.

## Glob syntax

Patterns are repository-relative POSIX paths. `*` matches within one path
segment, `?` matches one non-slash character, and `**` crosses directories.
Absolute, empty, `.` and `..` patterns are invalid. Existing symlinks in any
target component are refused even when their resolved destination stays inside
the root.

## Policy lifecycle

Every receipt stores the SHA-256 hash of the exact policy bytes. The v0.1
verifier requires all records in a journal to use the currently loaded policy.
When a human changes policy, independently archive the old policy and journal,
then start a new empty journal. Do not allow the editing agent to perform that
rotation.

Ready-to-copy policies live in [`profiles/`](../profiles). Review them before
use; repository layouts and authority files differ.
