# Agent Self-Edit Gate — Public Release Plan

Status: v0.1.0 release execution record. Target: an honest public alpha release.
Unchecked items require owner/account action or post-release operation.

## Release thesis

Coding agents increasingly edit their own prompts and skills, but the files that
define behaviour sit next to files that grant authority. Agent Self-Edit Gate
provides a deterministic, auditable write path for the behaviour layer while
keeping the authority layer protected.

Canonical public line:

> Policy-enforced self-edit gateway for coding agents: agents may improve their
> prompts and skills without rewriting permissions, hooks, or enforcement.

Add the portfolio signature after the claim:

> Built from operating a mixed Claude/Codex production fleet.

Never call it a generic firewall or sandbox.

## Phase 0 — Revalidate the opportunity

- [x] Search GitHub, PyPI, npm, HN, Reddit, and the web directly for self-edit
      policy tools. Use a browser user agent for sites hidden from search bots.
- [x] Recheck adjacent tools such as agent firewalls, package managers, policy
      gateways, protected-skills proposals, and native Claude/Codex controls.
- [x] Record dated findings and exact evidence URLs in `docs/COMPETITORS.md`.
- [x] Recheck the repository, PyPI, and command names. Decide whether the public
      command remains `selfedit-gate`.
- [x] Confirm the wedge still exists. Stop or reposition if a maintained direct
      peer already provides runtime self-edit zones plus independent receipts.
- [x] Choose a license. Apache-2.0 is the current recommendation because patent
      terms matter for a security-adjacent policy tool.

## Phase 1 — Security design before features

- [x] Write `docs/THREAT_MODEL.md`: assets, actors, prompt injection, direct
      shell/tool writes, policy tampering, receipt tampering, symlinks, traversal,
      crash points, and external trust anchors.
- [x] State the core limitation in the first README screen: without sandbox or
      filesystem policy making this gateway the only writer, it is convention,
      not enforcement.
- [x] Version the policy and receipt schemas.
- [x] Specify deny-before-allow overlap, extension rules, file/byte/diff limits,
      creation policy, ownership/permissions, and realpath containment.
- [x] Complete two-phase receipts: intent with before/policy hashes, atomic
      write, commit with after hash, and verifier handling for dangling intents.
- [x] Define how protected CI or another independent anchor verifies receipts.

Exit gate: an external reviewer can explain exactly what the tool stops, what
it cannot stop, and which deployment assumptions make the guarantee true.

## Phase 2 — Build and validate v0.1

- [x] Implement bounded `check`, exact `replace`, whole-file `write`, and
      `verify-receipts` commands.
- [x] Add generic, Claude Code, and Codex policy profiles; keep profiles data,
      not hard-coded product branches.
- [x] Add deterministic error codes and JSON output.
- [x] Add unit and integration tests for every policy branch.
- [x] Add hostile cases: symlink file/parent, traversal, race, ambiguous anchor,
      binary/extension mismatch, oversized diff, audit directory failure,
      interrupted write, stale intent, policy swap, receipt truncation.
- [x] Test on Linux and macOS; either support Windows or mark it unsupported.
- [ ] Arrange threat-model review with at least one independent security-minded
      user or design partner and resolve blocking findings.

Exit gate: all supported installs and hostile fixtures pass; no security claim
depends on the agent's own unrestricted testimony.

## Phase 3 — Package the repository

- [x] Select the final name, version, license, and public package metadata.
- [x] Upgrade README: problem, 15-second demo, honest boundary, quickstart,
      policy example, architecture, receipts, comparison table, limitations,
      roadmap, and portfolio signature.
- [ ] Add `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`,
      `CODE_OF_CONDUCT.md`, issue/PR templates, and 3–5 real `good first issue`s.
- [x] Add `docs/POLICY_REFERENCE.md`, `docs/RECEIPTS.md`, and deployment recipes.
- [x] Add `llms.txt` and an agent skill showing the safe edit workflow if useful.
- [x] Add CI for lint, type checking, tests, packaging, and hostile fixtures.
- [ ] Add OIDC trusted publishing for PyPI; never store a long-lived token.
- [x] Generate a 1280x640 social preview and a deterministic terminal demo.
- [ ] Configure GitHub description/topics with `ai-agents`, `coding-agents`,
      `policy-as-code`, `agent-security`, `claude-code`, `codex`, `python`, and
      `developer-tools` only where accurate.

## Phase 4 — Pre-public rehearsal

- [x] Install the built artifact in a clean temporary environment.
- [x] Run the full documented demo in a disposable repository.
- [x] Confirm every deny example fails and every allow example succeeds.
- [x] Inspect package contents, README rendering, links, wheel metadata, and
      source distribution.
- [x] Scan git history and files for secrets, private paths, customer data,
      organization names, internal IDs, and proprietary topology.
- [x] Run dependency/security scans and review generated artifacts.
- [x] Re-run the Phase 0 competitor and name checks on the day of launch.
- [ ] Prepare release notes, Show HN draft, native Reddit drafts, dev.to article,
      Habr adaptation, FAQ, and honest limitations before changing visibility.

## Phase 5 — Owner-authorized public flip

Do not execute this phase without an explicit owner instruction.

1. [ ] Configure a pending PyPI trusted publisher for this repository and
       `.github/workflows/release.yml`.
2. [ ] Change GitHub visibility to public.
3. [ ] Immediately confirm LICENSE, README/demo, description, topics, and clean
       history are visible.
4. [ ] Enable secret scanning, push protection, private vulnerability reporting,
       and CodeQL/default code scanning where available.
5. [ ] Upload social preview and pin the repository on the owner profile.
6. [ ] Tag `v0.1.0`; let CI publish through OIDC.
7. [ ] Create a GitHub Release with human notes, demo, limitations, and roadmap.
8. [ ] Verify provenance and install from PyPI in a clean environment.
9. [ ] Submit to appropriate agent-security and developer-tool awesome lists;
       do not submit to MCP directories unless the product actually ships MCP.

## Phase 6 — Launch content, days 2–14

- [ ] Wait at least one day after the flip so install paths can be exercised.
- [ ] Show HN, Tuesday–Thursday 15:00–18:00 Madrid time: link to GitHub and
      publish a technical maker comment with origin, threat model, and limits.
- [ ] Use different native posts on different days for relevant communities
      such as r/ClaudeCode, r/codex, r/opensource, and agent-security forums.
- [ ] Publish a story article: why self-editing agents need a privilege boundary.
- [ ] Publish a technical article: intent/commit receipts and independent trust.
- [ ] Publish a Russian Habr adaptation if it has a genuine technical angle.
- [ ] Submit to Console.dev or similar devtool newsletters after the repo is
      stable. Never buy stars or ask for coordinated votes.

## Phase 7 — Operate the release

- [ ] Respond to issues within 24 hours for the first two weeks.
- [ ] Track installs, stars, forks, external config references, security reports,
      and repeated use without adding product telemetry.
- [ ] Keep a public roadmap and produce focused releases with human changelogs.
- [ ] Cross-link the other OSS portfolio repositories only where relevant.
- [ ] After 60 days, continue active development only if at least three external
      adopters or design partners use it; otherwise freeze to maintenance.

## Actions reserved for the owner

Repository visibility, PyPI trusted-publisher account confirmation, public tag
and release authorization, directory/Marketplace submissions requiring account
consent, social-preview upload if API access is unavailable, profile pinning,
and posting from personal HN/Reddit/dev.to/Habr accounts.
