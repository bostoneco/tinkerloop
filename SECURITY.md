# Security Policy

Tinkerloop is currently private and in `alpha`-prep status.

## Reporting A Vulnerability

Do not open a public issue for a suspected vulnerability.

While the project is private:

- report security concerns through the maintainers' existing internal channels
- include reproduction steps, impact, and any relevant logs or artifacts
- state whether the issue affects example targets, the core engine, or adapter boundaries

Once the project becomes public, this policy should be updated with the public
security contact and supported release lines.

## Security Direction

Tinkerloop intentionally avoids production-action behavior.
The long-term remote-driver direction remains:

- target-owned
- non-prod only
- infrastructure-authenticated
- auditable

That direction is documented now so early contributions do not weaken the
eventual public security posture.
