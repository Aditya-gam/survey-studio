# Contributing to Survey Studio

Thank you for your interest in contributing! This document outlines the standards and workflow for contributing to Survey Studio.

## Branch Strategy

- Branch names follow Conventional Commits types:
  - `feat/<short-description>` for new features
  - `fix/<short-description>` for bug fixes
  - `chore/<short-description>` for maintenance tasks
  - `docs/<short-description>` for documentation-only changes
  - `refactor/<short-description>` for code refactors

- Branch protection and merging:
  - Rebase merge strategy only (no merge commits, keep linear history)
  - Require CI to pass (lint, type, tests, coverage) before merge
  - At least one code review approval
  - Do not delete branches automatically after merge (maintainers may keep history)

## Conventional Commits

Commit messages must follow the Conventional Commits specification:

```
<type>[optional scope]: <short summary>

[optional body]

[optional footer(s)]
```

Types include: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`.

Examples:

- `feat: add summarizer agent retries`
- `fix(ui): handle empty search queries`
- `docs: add architecture diagram`
- `refactor: extract arxiv client`
- `test: increase coverage for retry logic`
- `chore: bump ruff to latest`

Breaking changes:

- Indicate with `BREAKING CHANGE:` in the footer or use `!`, for example: `feat!: migrate to new API`

Commitizen is configured to help:

```bash
poetry run cz commit
poetry run cz check --rev-range origin/main..HEAD
```

## Local Development Workflow

Prerequisites: Python 3.12.11+, Poetry.

1. Clone and install:
   ```bash
   git clone https://github.com/Aditya-gam/survey-studio.git
   cd survey-studio
   poetry install --with dev
   ```
2. Install pre-commit hooks:
   ```bash
   poetry run pre-commit install
   poetry run pre-commit install --install-hooks
   ```
3. Set environment/secrets:
   ```bash
   export OPENAI_API_KEY="..."
   # or use .streamlit/secrets.toml for Streamlit
   ```
4. Start the app:
   ```bash
   poetry run streamlit run streamlit_app.py --server.port 8501
   ```
5. Run tests (95%+ coverage required):
   ```bash
   poetry run pytest
   ```
6. Lint and type check:
   ```bash
   poetry run ruff check .
   poetry run ruff format .
   poetry run pyright
   ```
7. Full code quality pipeline:
   ```bash
   poetry run pre-commit run --all-files
   ```

## Pull Request Guidelines

Before opening a PR, ensure:

- Code builds and runs locally
- Ruff clean, Pyright passing
- Tests added/updated; coverage ≥95%
- Docs updated (README, docstrings, CHANGELOG)
- No breaking changes, or clearly documented with migration notes
- Security considerations reviewed (no secrets committed, least-privilege tokens)
- Performance impact assessed for heavy operations

### PR Review Checklist

- [ ] Follows project coding style and guidelines
- [ ] Linting (Ruff) passes
- [ ] Type checking (Pyright) passes
- [ ] Tests pass locally with ≥95% coverage
- [ ] Documentation updated
- [ ] Breaking changes documented (if any)
- [ ] Security reviewed
- [ ] Performance evaluated

Thank you for contributing! 💙
