"""Custom exception types for Survey Studio.

These exceptions create clear error boundaries across modules. Catch and
re-raise with these to ensure user-friendly messaging at the UI layer and
structured logging in the core pipeline.
"""

from __future__ import annotations


class SurveyStudioError(Exception):
    """Base exception for all Survey Studio errors."""


class ArxivSearchError(SurveyStudioError):
    """Raised when arXiv search fails or returns invalid data."""


class AgentCreationError(SurveyStudioError):
    """Raised when agent or model client creation fails."""


class ValidationError(SurveyStudioError):
    """Raised when user input fails validation."""


class OrchestrationError(SurveyStudioError):
    """Raised for errors during multi-agent orchestration/streaming."""
