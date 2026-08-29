# Roadmap

The project is intentionally narrow. Roadmap items deepen the write/verification
boundary rather than grow a hosted agent platform.

## Candidate v0.2 work

- Detached Ed25519 signatures from an independently held verifier key.
- Explicit journal rotation manifest for reviewed policy upgrades.
- Recovery tooling that generates, but never auto-approves, dangling-intent plans.
- A small stdin/stdout broker protocol for OS-isolated deployments.
- Property-based glob, receipt-chain, and crash-point tests.
- Windows semantics after an equivalent no-follow/atomicity design is reviewed.

## Explicitly out of scope

No LLM classifier, hosted control plane, telemetry, agent orchestration, package
marketplace, secrets broker, semantic prompt scanner, or generic MCP firewall is
planned for the core.

Feature requests should explain the new security invariant and how it will be
tested. Scope expansion without a clear invariant will be declined.
