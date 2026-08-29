# Landscape and name check

Checked **2026-08-29** using direct GitHub Search/API, the PyPI JSON API, npm's
registry API, Hacker News' Algolia index, and official product documentation.
Direct Reddit JSON search returned HTTP 403 from this environment, so Reddit
evidence was limited to web-index results and was not treated as exhaustive.
Search indexes are incomplete; this is positioning evidence, not a trademark
clearance.

## Name availability

- GitHub searches for `"agent self-edit gate"` and `"selfedit-gate"` returned
  only this repository.
- PyPI returned HTTP 404 for `agent-self-edit-gate` and `selfedit-gate`.
- npm returned HTTP 404 for both names.
- Hacker News returned no exact `selfedit-gate` result. A broader query found
  one unrelated self-modifying agent, not a policy/receipt gateway.

The repository stays **Agent Self-Edit Gate**, the command stays
`selfedit-gate`, and the proposed Python distribution is
`agent-self-edit-gate`. Registry availability can change at any time.

## Adjacent products

| Product | Officially described scope | Difference from this project |
| --- | --- | --- |
| [Claude Code permissions](https://code.claude.com/docs/en/permissions) and [hooks](https://code.claude.com/docs/en/hooks) | Native tool permissions and lifecycle hooks | Engine-specific controls; this project supplies portable path zones and file receipts, but still needs an independent hook/sandbox anchor |
| [Codex security](https://developers.openai.com/codex/security) | Sandbox and approval controls | Provides the external execution boundary; does not define this project's portable self-edit policy/receipt protocol |
| [AgentGate](https://github.com/zihan001/agentgate) | Tool-call policy engine and runtime proxy | Broader tool-call interception, not a narrow behaviour-file writer |
| [Agent Gateway](https://github.com/agentgateway/agentgateway) | Agent/MCP/LLM connectivity, governance, and observability | Network/protocol gateway rather than repository self-edit zones |
| [MakerChecker](https://github.com/makerchecker/MakerChecker) | RBAC, approvals, segregation of duties, and signed audit logs | Broad agent action governance; materially larger scope and different enforcement point |
| [agentver](https://github.com/agentver/agentver) | Version and distribute skills across coding assistants | Skill supply-chain manager rather than runtime self-edit mutation gate |
| [mcp-firewall](https://github.com/ressl/mcp-firewall) | Policy/security gateway for MCP tool traffic | Intercepts MCP traffic, not deterministic local file mutation |

No maintained direct peer found in this check combined all four defining
elements: repository-local behaviour/authority zones, deny-before-allow exact
file mutation, two-phase file receipts, and a deliberately externalized trust
boundary. That narrow wedge remains useful. The README does not claim the field
is empty and does not use the overbroad phrase “firewall for AI agents.”
