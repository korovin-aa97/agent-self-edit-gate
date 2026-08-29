# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/korovin-aa97/agent-self-edit-gate/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/korovin-aa97/agent-self-edit-gate/releases/tag/v0.1.0
