# Security Policy

We take the security of Survey Studio seriously. Please follow this policy when reporting vulnerabilities or security concerns.

## Supported Versions

We aim to support the latest minor release on the `main` branch. Security fixes are applied to `main` and released promptly.

## Reporting a Vulnerability

Please report security issues privately:

- Email: gambhir.aditya19@gmail.com
- Do not open a public GitHub issue for vulnerabilities

We will acknowledge receipt within 48 hours and provide a timeline for resolution after triage.

## Disclosure Process

1. You report the issue privately
2. We confirm and triage severity
3. We prepare and test a fix
4. We coordinate a release with a changelog entry under Security
5. We credit the reporter (unless anonymity is requested)

## Security Best Practices for Contributors

- Do not commit secrets. Use environment variables or `.streamlit/secrets.toml`
- Follow least privilege for API keys (e.g., OpenAI)
- Validate and sanitize inputs; fail closed where appropriate
- Handle exceptions gracefully with meaningful logs
- Keep dependencies updated via Poetry lockfile and pre-commit checks

Thank you for helping keep Survey Studio secure.
