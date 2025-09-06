## PR Title

Short, descriptive title following Conventional Commits, e.g., `feat: add new summarizer retries`.

## Summary

Describe what this PR changes and why.

## Related Issues

Closes #<issue-number> (if applicable)

## Changes

-
-

## Screenshots / GIFs (UI changes)

Include before/after screenshots or a GIF if UI is affected.

## Testing Instructions

```bash
poetry install --with dev
poetry run pre-commit run --all-files
poetry run pytest
```

## Breaking Changes

- [ ] None
- If any, describe and provide migration steps:

## Deployment Considerations

- Env/secrets changes required?
- Data migrations?

## Pre-submission Checklist

- [ ] Code follows project style guidelines (Ruff clean)
- [ ] Type checking passes (mypy clean)
- [ ] Tests added/updated with ≥95% coverage
- [ ] Documentation updated (README, docstrings, CHANGELOG)
- [ ] No breaking changes (or properly documented)
- [ ] Security considerations reviewed
- [ ] Performance impact assessed
