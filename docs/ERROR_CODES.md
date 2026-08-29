# Error codes

All policy, input, target, atomic-write, and receipt refusals exit with status
`2`. With `--json`, the shape is stable:

```json
{"error":{"code":"E_ZONE_DENIED","message":"..."},"ok":false}
```

| Family | Codes | Meaning |
| --- | --- | --- |
| Policy | `E_POLICY_*` | unreadable, unsupported, ambiguous, changed, or unsafe policy |
| Path | `E_PATH`, `E_TRAVERSAL`, `E_OUTSIDE_ROOT`, `E_SYMLINK`, `E_PARENT` | target path cannot be safely classified or anchored |
| Zone | `E_ZONE_DENIED`, `E_ZONE_UNMATCHED`, `E_EXTENSION` | deny-before-allow or extension refusal |
| Input | `E_INPUT_READ`, `E_INPUT_SIZE`, `E_SIZE`, `E_DIFF_SIZE`, `E_BINARY`, `E_ENCODING` | proposed bytes violate a bound |
| Replacement | `E_EMPTY_ANCHOR`, `E_ANCHOR_COUNT`, `E_TARGET_STALE` | exact replacement is empty, ambiguous, missing, or stale |
| Target | `E_TARGET_*`, `E_CREATE_DENIED`, `E_NOT_FOUND` | file type, owner, identity, existence, or concurrent state is unsafe |
| Atomic write | `E_ATOMIC_WRITE` | durable temporary write or atomic replacement failed |
| Audit | `E_AUDIT_*` | journal path, framing, sequence, chain, hash, or persistence failed |
| Receipt | `E_RECEIPT_*`, `E_DANGLING_INTENT`, `E_FILE_CHAIN`, `E_CURRENT_HASH` | semantic operation chain or current file does not verify |

Messages may gain detail in compatible releases. Scripts should branch on the
code, not parse English text. Argument-parser usage errors exit `2` using
standard `argparse` output and are not part of the JSON contract in v0.1.
