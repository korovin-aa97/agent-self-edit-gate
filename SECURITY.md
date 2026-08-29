# Security policy

## Supported versions

| Version | Supported |
| --- | --- |
| 0.1.x | Yes |
| < 0.1 | No |

v0.1 is alpha software and has not received an independent professional audit.
The core limitation in the [threat model](docs/THREAT_MODEL.md) is not a
vulnerability: unrestricted writers can bypass a local CLI by design.

## Reporting a vulnerability

Use GitHub's **Report a vulnerability** form under the repository Security tab.
Do not open a public issue. Include affected version, platform/filesystem,
policy, reproduction, impact, and whether the agent had an alternate write path.

You should receive acknowledgement within 72 hours and a status update within
seven days. We aim to coordinate a fix and disclosure within 90 days, but may
move faster for actively exploited issues. Please avoid accessing other
people's data, degrading services, or publishing details before a fix is ready.

No bug bounty is currently offered.
