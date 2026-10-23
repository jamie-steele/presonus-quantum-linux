# Security Policy

## Supported Versions

PreSonus Quantum Linux is an experimental project. Security fixes are provided on a best-effort basis, without a guaranteed response or release schedule.

| Version or component | Security maintenance |
| --- | --- |
| Latest RFC release with the latest native packaging revision | Best effort |
| Current `master` branch | Fixes developed here |
| Older releases and packaging revisions | No dedicated backports |
| In-house `snd-quantum2626` research fallback | No separately maintained security release |

Use the latest available packaging revision even when the underlying RFC version has not changed.

## Reporting a Vulnerability

Please report suspected vulnerabilities privately using [GitHub’s vulnerability reporting form](https://github.com/jamie-steele/presonus-quantum-linux/security/advisories/new).

Do not post exploit details, sensitive logs, or working proofs of concept in public issues before coordinated disclosure.

Include, where available:

- Affected release, package revision, or commit.
- Linux distribution and kernel version.
- Driver backend: `snd-quantum` or `snd-quantum2626`.
- Expected security impact and any required privileges or physical access.
- Reproduction steps and a minimal proof of concept.
- Relevant sanitized logs.

Remove credentials, personal information, and machine identifiers. Do not upload proprietary driver binaries or large raw captures.

## Response and Disclosure

We aim to acknowledge reports within seven days and provide progress updates approximately every two weeks while investigating. These are targets, not guarantees.

If a report is accepted, we will coordinate investigation, remediation, and disclosure with the reporter. Issues affecting upstream driver code may require coordination with its upstream author or the relevant Linux maintainers.

If a report is declined, we will explain the reason where possible. Disclosure timing will depend on the impact, available fixes, and any upstream coordination.

## Other Bugs

For installation problems, missing audio devices, playback issues, or crashes without an identified security impact, use the [public issue tracker](https://github.com/jamie-steele/presonus-quantum-linux/issues). If you suspect a security impact, report privately first.
