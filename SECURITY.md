# Security Policy

This document is the root security entry point for MiroConsumer. The expanded operating notes live in `docs/security.md`, but this file is complete enough for maintainers, scanners, and external reporters to use directly.

## Supported Versions

| Version | Status | Notes |
| --- | --- | --- |
| 0.7.x | Supported | Current release line. Security fixes and dependency updates are accepted. |
| 0.6.x | Limited support | Security fixes only when they are low risk to backport. |
| < 0.6 | Unsupported | Upgrade before requesting fixes. |

## Reporting a Vulnerability

Please do not open a public issue for a suspected vulnerability.

Preferred channel: GitHub Security Advisories for the repository.

Fallback channel: email `security@miroconsumer.dev` with the subject prefix `[SECURITY]`.

Include the following information when possible:

- A short description of the vulnerability and affected component.
- Reproduction steps or a minimal proof of concept.
- Expected impact, including data exposure, tenant isolation, or service availability concerns.
- A suggested fix or mitigation if you already have one.
- Your preferred contact method for follow-up.

## Response SLA

| Severity | First Response | Target Fix | Disclosure Target |
| --- | --- | --- | --- |
| Critical | 24 hours | 7 days | 30 days after fix |
| High | 72 hours | 30 days | 30 days after fix |
| Medium | 7 days | 90 days | Next regular release |
| Low | 30 days | Best effort | Next regular release |

Severity is based on CVSS, exploitability, tenant boundary impact, and whether the issue affects default production deployment.

## Security Practices

- Run `bandit -r backend/app/ -ll --skip B101` before release.
- Run `pip-audit` against the backend dependency set before release.
- Keep container images non-root and prefer Python 3.12 runtime images.
- Rotate `SECRET_KEY`, API keys, JWT signing material, and LLM provider keys on a planned schedule.
- Keep MinIO console access bound to localhost or an internal management network.
- Treat prompt injection as a security issue when it can alter system/developer instructions, cross tenant boundaries, or exfiltrate hidden context.
- Do not commit real credentials, customer data, production prompts, or incident artifacts.

## Contact Roles

| Role | Contact | Responsibility |
| --- | --- | --- |
| Security owner | `security@miroconsumer.dev` | Vulnerability triage and remediation coordination. |
| SRE on-call | `sre-oncall@miroconsumer.dev` | Production incident coordination and rollback. |
| Maintainers | GitHub Security Advisory thread | Patch review and release notes. |

## AGPL-3.0 Notice

MiroConsumer is distributed under AGPL-3.0. If you deploy a modified network service, make the complete corresponding source available to users as required by the license.

## Related Documents

- `docs/security.md` for deeper security design notes.
- `.github/workflows/security.yml` for automated dependency, SAST, and secret checks.
- `.trivyignore` for reviewed container vulnerability exceptions.