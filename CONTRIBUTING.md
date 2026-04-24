# Contributing to TradeNodeX

Thank you for your interest in improving TradeNodeX.

This repository welcomes contributions that improve reliability, documentation, tests, user experience, deployment clarity, security posture, and connector compatibility.

## Contribution principles

- Keep changes small, reviewable, and well-scoped.
- Do not commit secrets, API keys, local databases, private logs, or screenshots containing sensitive information.
- Prefer documentation and tests when changing behavior.
- Keep public claims conservative and verifiable.
- Respect third-party trademarks and do not add exchange logos or copied proprietary assets.

## Good first contribution areas

- Documentation improvements
- Deployment notes
- Test coverage
- Error-message clarity
- UI usability improvements
- Security hardening notes
- Internationalization and translation improvements

## Development workflow

1. Fork the repository.
2. Create a topic branch.
3. Make a focused change.
4. Run the relevant checks.
5. Open a pull request using the PR template.

Backend tests:

```bash
python -m pytest -q
```

Frontend checks from the `frontend/` workspace:

```bash
node node_modules/typescript/bin/tsc --noEmit
node node_modules/vite/bin/vite.js build
```

## Pull request checklist

Before opening a PR, please confirm:

- The change is scoped and easy to review.
- No secrets or private data are included.
- Documentation is updated when behavior or usage changes.
- Tests or validation notes are included where appropriate.
- The PR description explains the reason for the change.

## Code of conduct

Be respectful, precise, and constructive. This project is intended to remain practical, security-conscious, and operator-focused.