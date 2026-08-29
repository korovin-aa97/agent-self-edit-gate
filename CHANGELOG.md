# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2026-08-30

### Fixed

- Reject non-integer policy/receipt schema fields and malformed zone modes with
  deterministic errors instead of accepting booleans or leaking a traceback.
- Refuse group/world-writable receipt directories, hard-linked receipt files,
  and receipt paths that resolve to the policy root.
- Open target, receipt, and CLI input files non-blocking so FIFOs fail closed
  instead of hanging the gateway.
- Use a bounded temporary filename so valid long target names remain writable.
- Fail before replacement when existing ownership cannot be restored.
- Replace stale, non-runnable README examples and record the live PyPI install.

### Changed

- Build releases from a checked tag, attach tested artifacts to a draft, and
  publish only after assets, checksums, and attestations are present.
- Pin GitHub Actions to full commit SHAs and publish to PyPI from the exact
  immutable GitHub Release assets.

## [0.1.0] - 2026-08-29

### Added

- Versioned TOML policy with deny-before-allow mutable, protected, and immutable zones.
- Bounded `check`, exact `replace`, whole-file `write`, and `verify-receipts` commands.
- Atomic local-filesystem writes with symlink, traversal, race, ownership, type,
  encoding, extension, file-size, and changed-byte checks.
- Versioned two-phase intent/commit receipt protocol with ordered SHA-256 chain.
- Stable JSON output and deterministic error codes.
- Generic, Claude Code, and Codex policy profiles.
- Threat model, protocol references, deployment recipes, hostile tests, packaging,
  CI, security policy, and community files.

[Unreleased]: https://github.com/korovin-aa97/agent-self-edit-gate/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/korovin-aa97/agent-self-edit-gate/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/korovin-aa97/agent-self-edit-gate/releases/tag/v0.1.0
