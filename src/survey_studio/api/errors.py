"""FastAPI exception handlers for Survey Studio.

This module provides custom exception handlers that integrate with the
existing Survey Studio error classes and return properly formatted
JSON error responses following FastAPI conventions.
"""

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

from survey_studio.core.errors import (
    ConfigurationError,
    ExportError,
    ExternalServiceError,
    LLMError,
    OrchestrationError,
    SurveyStudioError,
    ValidationError,
    get_error_details,
)
from survey_studio.schemas import (
    ConfigurationErrorResponse,
    ErrorResponse,
    ExternalServiceErrorResponse,
    ValidationErrorResponse,
)


def survey_studio_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Handle Survey Studio custom exceptions.

    Args:
        _request: The FastAPI request object
        exc: The Survey Studio exception

    Returns:
        JSONResponse with appropriate error details and status code
    """
    if not isinstance(exc, SurveyStudioError):
        # Fallback to general exception handler
        return general_exception_handler(_request, exc)

    error_details = get_error_details(exc)

    # Map Survey Studio errors to HTTP status codes
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR  # Default

    if isinstance(exc, ValidationError):
        status_code = status.HTTP_400_BAD_REQUEST
    elif isinstance(exc, ConfigurationError):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif isinstance(exc, ExternalServiceError | LLMError):
        status_code = status.HTTP_502_BAD_GATEWAY
    elif isinstance(exc, ExportError | OrchestrationError):
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    # Create appropriate response model based on error type
    if isinstance(exc, ValidationError):
        response_data = ValidationErrorResponse(
            error=exc.user_message,
            error_type=error_details["type"],
            error_id=error_details.get("error_id"),
            timestamp=error_details.get("timestamp", ""),
            context=error_details.get("context"),
            field=error_details.get("context", {}).get("field"),
        ).model_dump(exclude_none=True)
    elif isinstance(exc, ConfigurationError):
        response_data = ConfigurationErrorResponse(
            error=exc.user_message,
            error_type=error_details["type"],
            error_id=error_details.get("error_id"),
            timestamp=error_details.get("timestamp", ""),
            context=error_details.get("context"),
        ).model_dump(exclude_none=True)
    elif isinstance(exc, ExternalServiceError):
        response_data = ExternalServiceErrorResponse(
            error=exc.user_message,
            error_type=error_details["type"],
            error_id=error_details.get("error_id"),
            timestamp=error_details.get("timestamp", ""),
            context=error_details.get("context"),
            service=error_details.get("context", {}).get("service"),
        ).model_dump(exclude_none=True)
    else:
        response_data = ErrorResponse(
            error=exc.user_message,
            error_type=error_details["type"],
            error_id=error_details.get("error_id"),
            timestamp=error_details.get("timestamp", ""),
            context=error_details.get("context"),
        ).model_dump(exclude_none=True)

    return JSONResponse(
        status_code=status_code,
        content=response_data,
    )


def http_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Handle FastAPI HTTP exceptions.

    Args:
        _request: The FastAPI request object
        exc: The HTTP exception

    Returns:
        JSONResponse with error details
    """
    if not isinstance(exc, HTTPException):
        # Fallback to general exception handler
        return general_exception_handler(_request, exc)

    response_data = ErrorResponse(
        error=str(exc.detail),
        error_type="HTTPException",
        error_id=None,
        context=None,
    ).model_dump(exclude_none=True)

    return JSONResponse(
        status_code=exc.status_code,
        content=response_data,
    )


def general_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions.

    Args:
        _request: The FastAPI request object
        exc: The unexpected exception

    Returns:
        JSONResponse with generic error message
    """
    error_details = get_error_details(exc)

    response_data = ErrorResponse(
        error=error_details["user_message"],
        error_type=error_details["type"],
        error_id=None,
        context=None,
    ).model_dump(exclude_none=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=response_data,
    )


# Exception handler mapping for FastAPI app registration
EXCEPTION_HANDLERS = {
    SurveyStudioError: survey_studio_error_handler,
    HTTPException: http_exception_handler,
    Exception: general_exception_handler,
}
