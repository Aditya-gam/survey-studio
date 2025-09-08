"""Custom exception types for Survey Studio.

These exceptions create clear error boundaries across modules. Catch and
re-raise with these to ensure user-friendly messaging at the UI layer and
structured logging in the core pipeline.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
import uuid


class ErrorSeverity(Enum):
    """Error severity levels for classification and handling."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class SurveyStudioError(Exception):
    """Base exception for all Survey Studio errors."""

    def __init__(
        self,
        message: str = "An error occurred",
        *,
        user_message: str | None = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        original_exception: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.user_message = user_message or message
        self.severity = severity
        self.context = context or {}
        self.original_exception = original_exception
        self.error_id = uuid.uuid4().hex[:8]
        self.timestamp = datetime.now().isoformat()


class ConfigurationError(SurveyStudioError):
    """Raised for missing/invalid configuration (API keys, model settings)."""

    def __init__(self, message: str = "Configuration error", **kwargs: Any) -> None:
        super().__init__(
            message,
            user_message="Configuration issue detected. Please check your settings.",
            severity=ErrorSeverity.ERROR,
            **kwargs,
        )


class ExternalServiceError(SurveyStudioError):
    """Raised for arXiv API failures, network timeouts, service unavailability."""

    def __init__(
        self,
        message: str = "External service error",
        service: str = "unknown",
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        context["service"] = service
        super().__init__(
            message,
            user_message=(
                f"The {service} service is temporarily unavailable. "
                "Please try again in a few moments."
            ),
            severity=ErrorSeverity.WARNING,
            context=context,
            **kwargs,
        )


class LLMError(SurveyStudioError):
    """Raised for OpenAI API failures, rate limits, model errors, token limits."""

    def __init__(
        self,
        message: str = "LLM service error",
        model: str | None = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if model:
            context["model"] = model
        super().__init__(
            message,
            user_message=(
                "AI service encountered an issue. Please try again or contact "
                "support if the problem persists."
            ),
            severity=ErrorSeverity.ERROR,
            context=context,
            **kwargs,
        )


class ValidationError(SurveyStudioError):
    """Raised when user input fails validation."""

    def __init__(
        self, message: str = "Validation error", field: str | None = None, **kwargs: Any
    ) -> None:
        context = kwargs.pop("context", {})
        if field:
            context["field"] = field
        super().__init__(
            message,
            user_message=message,  # Validation errors are already user-friendly
            severity=ErrorSeverity.INFO,
            context=context,
            **kwargs,
        )


class ExportError(SurveyStudioError):
    """Raised for file generation, download failures, format conversion errors."""

    def __init__(
        self,
        message: str = "Export error",
        format_type: str | None = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if format_type:
            context["format"] = format_type
        super().__init__(
            message,
            user_message=(
                "Export failed. Please try again or contact support if the " "problem persists."
            ),
            severity=ErrorSeverity.WARNING,
            context=context,
            **kwargs,
        )


# Legacy exceptions - enhanced with new attributes
class ArxivSearchError(ExternalServiceError):
    """Raised when arXiv search fails or returns invalid data."""

    def __init__(self, message: str = "arXiv search error", **kwargs: Any) -> None:
        super().__init__(message, service="arXiv", **kwargs)


class AgentCreationError(LLMError):
    """Raised when agent or model client creation fails."""

    def __init__(self, message: str = "Agent creation error", **kwargs: Any) -> None:
        # Don't pass user_message twice - LLMError already sets it
        kwargs.pop("user_message", None)  # Remove if present to avoid conflict
        super().__init__(message, **kwargs)
        # Override the user_message from LLMError with our specific one
        self.user_message = "Failed to initialize AI agents. Please check your API configuration."


class OrchestrationError(SurveyStudioError):
    """Raised for errors during multi-agent orchestration/streaming."""

    def __init__(self, message: str = "Orchestration error", **kwargs: Any) -> None:
        super().__init__(
            message,
            user_message="Agent coordination failed. Please try again.",
            severity=ErrorSeverity.ERROR,
            **kwargs,
        )


def get_user_friendly_message(error: Exception) -> str:
    """Get a user-friendly message for any exception.

    Maps Survey Studio errors to their user_message attribute,
    and provides generic messages for other exception types.
    """
    if isinstance(error, SurveyStudioError):
        return error.user_message

    # Map common Python exceptions to user-friendly messages
    error_messages = {
        ConnectionError: (
            "Network connection failed. Please check your internet connection " "and try again."
        ),
        TimeoutError: "Request timed out. Please try again in a few moments.",
        KeyError: "Missing required data. Please check your configuration.",
        ValueError: "Invalid data provided. Please check your inputs and try again.",
        FileNotFoundError: "Required file not found. Please check your file paths.",
        PermissionError: "Permission denied. Please check your access rights.",
    }

    for exc_type, message in error_messages.items():
        if isinstance(error, exc_type):
            return message

    return (
        "An unexpected error occurred. Please try again or contact support "
        "if the problem persists."
    )


def get_error_details(error: Exception) -> dict[str, Any]:
    """Extract structured error details for logging and debugging."""
    details: dict[str, Any] = {
        "type": error.__class__.__name__,
        "message": str(error),
        "user_message": get_user_friendly_message(error),
    }

    if isinstance(error, SurveyStudioError):
        details.update(
            {
                "error_id": error.error_id,
                "severity": error.severity.value,
                "timestamp": error.timestamp,
                "context": error.context,
            }
        )

        if error.original_exception:
            details["original_error"] = {
                "type": error.original_exception.__class__.__name__,
                "message": str(error.original_exception),
            }

    return details
