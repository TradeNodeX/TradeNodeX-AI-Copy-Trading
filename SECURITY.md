# Security Policy

TradeNodeX is self-hosted infrastructure software. Users are responsible for deployment security, credential handling, server hardening, exchange permissions, and operational controls.

## Supported versions

The `main` branch is the active development branch for the open-source edition.

## Reporting a vulnerability

Please do not open a public GitHub issue for security-sensitive reports.

A useful report should include:

- A clear description of the issue
- Affected component or file path if known
- Reproduction steps or proof of concept
- Potential impact
- Suggested mitigation if available

Do not include real exchange credentials, private keys, local databases, production logs, or screenshots containing secrets.

## Credential handling rules

- Never enable withdrawal permission on exchange API keys used with this project.
- Prefer IP allowlists where the exchange supports them.
- Store secrets using a secure environment or secret-management layer.
- Do not commit `.env`, databases, logs, or local configuration files.
- Rotate credentials immediately if exposure is suspected.

## Deployment hardening checklist

- Use a fixed outbound IP for exchange allowlists.
- Restrict inbound ports.
- Use HTTPS behind a trusted reverse proxy for remote access.
- Apply operating-system security updates.
- Use least-privilege service accounts.
- Back up configuration and audit data securely.
- Monitor logs for unexpected errors or access patterns.

## Public disclosure

Security issues should be disclosed only after a fix or mitigation path is available. The goal is to protect users and prevent avoidable exposure.