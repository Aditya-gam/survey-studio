"""Survey Studio - Literature Review Assistant API.

This module provides the core functionality for conducting literature reviews
using AutoGen agents. The main functions are available in the api module.
"""

from .api import (
    generate_export,
    get_available_models,
    get_health_status,
    get_provider_status,
    initialize_session,
    run_literature_review,
    run_review_with_fallback,
    validate_review_request,
)

__all__ = [
    "initialize_session",
    "get_provider_status",
    "validate_review_request",
    "run_literature_review",
    "run_review_with_fallback",
    "generate_export",
    "get_available_models",
    "get_health_status",
]


def main() -> None:
    """Main entry point - redirects to API module."""
    from .api import main as api_main  # noqa: PLC0415

    api_main()


if __name__ == "__main__":
    main()
