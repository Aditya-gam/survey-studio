#!/bin/bash
# Standard linting and formatting script
# This ensures consistency between manual runs and pre-commit

set -e

echo "🧹 Running ruff format..."
ruff format --config=pyproject.toml .

echo "🔍 Running ruff check with fixes..."
ruff check --fix --config=pyproject.toml .

echo "✅ All linting and formatting complete!"
