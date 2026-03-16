# Security Policy

Tinkerloop is in **alpha**; security reporting is taken seriously.

## Reporting a vulnerability

**Do not open a public issue** for a suspected vulnerability.

Report security concerns privately:

- **Preferred:** [Open a private security advisory](https://github.com/bostoneco/tinkerloop/security/advisories/new) on GitHub.
- Include reproduction steps, impact, and any relevant logs or artifacts.
- State whether the issue affects example targets, the core engine, or adapter boundaries.

## Supported release lines

For the alpha release, the current main line is in scope. Security fixes will be documented in [CHANGELOG.md](CHANGELOG.md) and release notes.

## Security Direction

Tinkerloop intentionally avoids production-action behavior.
The long-term remote-driver direction remains:

- target-owned
- non-prod only
- infrastructure-authenticated
- auditable

That direction is documented now so early contributions do not weaken the
eventual public security posture.
