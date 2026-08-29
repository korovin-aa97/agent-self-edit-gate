# Agent Self-Edit Gate v0.1.1

v0.1.1 is a focused hardening and release-quality patch for the public alpha.
It preserves policy schema v1, receipt schema v1, and the four CLI commands.

## Security and correctness fixes

- Receipt journals now refuse unsafe parent-directory modes and hard links.
- FIFO targets, journals, and CLI input files fail closed instead of blocking.
- Policy and receipt schema versions require actual integers; malformed zone
  modes return deterministic policy errors rather than Python tracebacks.
- Atomic writes use a short bounded temporary name, so valid long target names
  work on supported filesystems.
- A failure to restore existing ownership aborts before target replacement.

## Release integrity

- Every GitHub Action is pinned to a full commit SHA.
- The release workflow validates the tag, package version, main ancestry, and
  all required checks; tests wheel and sdist; then attaches assets and checksums
  to a draft before publishing the immutable release.
- PyPI receives the exact assets verified from that immutable GitHub Release.

## Documentation

The README's demo and quickstart were replayed from a clean checkout and now use
real files. The live PyPI install and the policy-relative `root` rule are stated
explicitly.

## Install

```bash
python -m pip install "agent-self-edit-gate==0.1.1"
selfedit-gate --version
```

Python 3.12+ on local Linux and macOS filesystems is supported. The central
boundary remains unchanged: an external sandbox, protected broker, or protected
CI must prevent direct writes around the gate. v0.1.1 has not received an
independent professional security audit.
