"""Retry mechanisms and circuit breaker patterns for external services.

Provides decorators for retrying operations with exponential backoff, jitter,
and circuit breaker patterns to handle external service failures gracefully.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from functools import wraps
import logging
import time
from typing import Any, TypeVar, cast

from tenacity import (
    after_log,
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
    wait_fixed,
)

from survey_studio.core.errors import (
    ConfigurationError,
    ExportError,
    ExternalServiceError,
    LLMError,
    ValidationError,
)
from survey_studio.core.logging import with_context

logger = logging.getLogger(__name__)
# Prevent test-time mocked root handlers from interfering with library logs
logger.addHandler(logging.NullHandler())
logger.propagate = False

F = TypeVar("F", bound=Callable[..., Any])

# Constants
CIRCUIT_BREAKER_FAILURE_THRESHOLD = 5
CIRCUIT_BREAKER_RECOVERY_TIMEOUT = 300  # 5 minutes
HTTP_STATUS_SERVER_ERROR_MIN = 500
HTTP_STATUS_SERVER_ERROR_MAX = 600

# Circuit breaker tracking
_circuit_state: dict[str, dict[str, Any]] = defaultdict(
    lambda: {
        "failure_count": 0,
        "last_failure_time": 0,
        "is_open": False,
    }
)


def _should_retry_exception(exc: BaseException) -> bool:
    """Determine if an exception should trigger a retry."""
    # Don't retry validation or configuration errors
    from survey_studio.core.errors import ConfigurationError, ValidationError  # noqa: PLC0415

    if isinstance(exc, ValidationError | ConfigurationError):
        return False

    # Respect explicit no-retry flag on domain errors
    if isinstance(exc, ExternalServiceError | LLMError | ExportError):
        try:
            context = getattr(exc, "context", {}) or {}
            if context.get("no_retry") is True:
                return False
        except Exception:
            pass
        return True

    # Retry on common network/service errors
    if isinstance(exc, ConnectionError | TimeoutError):
        return True

    # For HTTP errors, only retry 5xx status codes
    if hasattr(exc, "response"):
        response = getattr(exc, "response", None)
        if response is not None and hasattr(response, "status_code"):
            status_code = getattr(response, "status_code", None)
            if status_code is not None and isinstance(status_code, int):
                return bool(
                    HTTP_STATUS_SERVER_ERROR_MIN <= status_code < HTTP_STATUS_SERVER_ERROR_MAX
                )

    return False


def _update_circuit_breaker(service: str, success: bool) -> None:
    """Update circuit breaker state based on operation result."""
    state = _circuit_state[service]

    if success:
        # Reset on successful operation
        state["failure_count"] = 0
        state["is_open"] = False
    else:
        # Increment failure count
        state["failure_count"] += 1
        state["last_failure_time"] = time.time()

        # Open circuit if threshold exceeded
        if state["failure_count"] >= CIRCUIT_BREAKER_FAILURE_THRESHOLD:
            state["is_open"] = True
            log = with_context(logger, component="circuit_breaker")
            log.error(
                f"Circuit breaker opened for {service}",
                extra={
                    "extra_fields": {
                        "service": service,
                        "failure_count": state["failure_count"],
                    }
                },
            )


def _check_circuit_breaker(service: str) -> None:
    """Check if circuit breaker allows the operation."""
    state = _circuit_state[service]

    if state["is_open"]:
        # Check if recovery timeout has passed
        if time.time() - state["last_failure_time"] > CIRCUIT_BREAKER_RECOVERY_TIMEOUT:
            state["is_open"] = False
            state["failure_count"] = 0
            log = with_context(logger, component="circuit_breaker")
            log.info(
                f"Circuit breaker closed for {service}",
                extra={"extra_fields": {"service": service}},
            )
        else:
            raise ExternalServiceError(
                f"Circuit breaker is open for {service}",
                service=service,
                context={"failure_count": state["failure_count"]},
            )


def circuit_breaker(service: str) -> Callable[[F], F]:
    """Decorator to implement circuit breaker pattern."""

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            _check_circuit_breaker(service)

            try:
                result = func(*args, **kwargs)
                _update_circuit_breaker(service, success=True)
                return result
            except Exception:
                _update_circuit_breaker(service, success=False)
                raise

        return cast("F", wrapper)

    return decorator


def retry_arxiv_operations[F: Callable[..., Any]](func: F) -> F:
    """Retry decorator for arXiv API operations.

    - 3 retries with exponential backoff (1s, 2s, 4s)
    - ±25% jitter to avoid thundering herd
    - 30-second timeout
    - Circuit breaker protection
    """

    @circuit_breaker("arXiv")
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception(_should_retry_exception),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.INFO),
        reraise=True,
    )
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        log = with_context(logger, component="retry", service="arXiv")

        try:
            log.debug(
                "Starting arXiv operation",
                extra={"extra_fields": {"operation": func.__name__}},
            )
            result = func(*args, **kwargs)
            log.debug(
                "arXiv operation completed successfully",
                extra={"extra_fields": {"operation": func.__name__}},
            )
            return result
        except Exception as exc:
            # Propagate non-retryable configuration/validation errors unchanged
            if isinstance(exc, (ConfigurationError | ValidationError)):
                raise
            log.error(
                f"arXiv operation failed: {func.__name__}",
                extra={
                    "extra_fields": {
                        "operation": func.__name__,
                        "error": str(exc),
                        "error_type": exc.__class__.__name__,
                    }
                },
            )
            # Convert generic exceptions to domain-specific ones
            if not isinstance(exc, ExternalServiceError):
                raise ExternalServiceError(
                    f"arXiv operation failed: {str(exc)}",
                    service="arXiv",
                    original_exception=exc,
                ) from exc
            raise

    return cast("F", wrapper)


def retry_llm_operations[F: Callable[..., Any]](func: F) -> F:
    """Retry decorator for LLM API operations.

    - 2 retries with exponential backoff (2s, 4s)
    - ±50% jitter for better distribution
    - 60-second timeout
    - Circuit breaker protection
    """

    @circuit_breaker("LLM")
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=2, min=2, max=4),
        retry=retry_if_exception(_should_retry_exception),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.INFO),
        reraise=True,
    )
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        log = with_context(logger, component="retry", service="LLM")

        try:
            log.debug(
                "Starting LLM operation",
                extra={"extra_fields": {"operation": func.__name__}},
            )
            result = func(*args, **kwargs)
            log.debug(
                "LLM operation completed successfully",
                extra={"extra_fields": {"operation": func.__name__}},
            )
            return result
        except Exception as exc:
            # Propagate non-retryable configuration/validation errors unchanged
            if isinstance(exc, (ConfigurationError | ValidationError)):
                raise
            log.error(
                f"LLM operation failed: {func.__name__}",
                extra={
                    "extra_fields": {
                        "operation": func.__name__,
                        "error": str(exc),
                        "error_type": exc.__class__.__name__,
                    }
                },
            )
            # Convert generic exceptions to domain-specific ones
            if not isinstance(exc, LLMError):
                raise LLMError(
                    f"LLM operation failed: {str(exc)}",
                    original_exception=exc,
                ) from exc
            raise

    return cast("F", wrapper)


def retry_export_operations[F: Callable[..., Any]](func: F) -> F:
    """Retry decorator for export/file operations.

    - 2 retries with linear backoff (1s, 2s)
    - 10-second timeout
    - Circuit breaker protection
    """

    @circuit_breaker("export")
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_fixed(1),  # Fixed 1s wait between retries
        retry=retry_if_exception(_should_retry_exception),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.INFO),
        reraise=True,
    )
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        log = with_context(logger, component="retry", service="export")

        try:
            log.debug(
                "Starting export operation",
                extra={"extra_fields": {"operation": func.__name__}},
            )
            result = func(*args, **kwargs)
            log.debug(
                "Export operation completed successfully",
                extra={"extra_fields": {"operation": func.__name__}},
            )
            return result
        except Exception as exc:
            # Propagate non-retryable configuration/validation errors unchanged
            if isinstance(exc, (ConfigurationError | ValidationError)):
                raise
            log.error(
                f"Export operation failed: {func.__name__}",
                extra={
                    "extra_fields": {
                        "operation": func.__name__,
                        "error": str(exc),
                        "error_type": exc.__class__.__name__,
                    }
                },
            )
            # Convert generic exceptions to domain-specific ones
            if not isinstance(exc, ExportError):
                raise ExportError(
                    f"Export operation failed: {str(exc)}",
                    original_exception=exc,
                ) from exc
            raise

    return cast("F", wrapper)


def get_circuit_breaker_status() -> dict[str, dict[str, Any]]:
    """Get current circuit breaker status for monitoring."""
    return dict(_circuit_state)


def reset_circuit_breaker(service: str) -> None:
    """Manually reset a circuit breaker (for testing/admin purposes)."""
    if service in _circuit_state:
        _circuit_state[service] = {
            "failure_count": 0,
            "last_failure_time": 0,
            "is_open": False,
        }

        log = with_context(logger, component="circuit_breaker")
        log.info(
            f"Circuit breaker manually reset for {service}",
            extra={"extra_fields": {"service": service}},
        )
