"""Unit tests for retry mechanisms and decorators.

Tests retry behavior, circuit breaker functionality, and timeout handling
for the tenacity-based retry system.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Generator
from unittest.mock import Mock, patch

import pytest

from survey_studio.errors import (
    ConfigurationError,
    ExportError,
    ExternalServiceError,
    LLMError,
    ValidationError,
)
from survey_studio.retry import (
    _check_circuit_breaker,
    _log_retry_attempt,
    _should_retry_exception,
    _update_circuit_breaker,
    circuit_breaker,
    get_circuit_breaker_status,
    reset_circuit_breaker,
    retry_arxiv_operations,
    retry_export_operations,
    retry_llm_operations,
)

# Test constants
EXPECTED_RETRY_ATTEMPTS = 3
EXPECTED_RETRY_ATTEMPTS_2 = 2
CIRCUIT_BREAKER_THRESHOLD = 5
EXPECTED_ATTEMPT_NUMBER = 2


class TestRetryDecorators:
    """Test retry decorator behavior."""

    @patch("survey_studio.retry.logger")
    def test_retry_arxiv_success_on_first_attempt(self, mock_logger: Mock) -> None:
        """Test successful operation on first attempt."""

        @retry_arxiv_operations
        def test_function() -> str:
            return "success"

        result = test_function()
        assert result == "success"
        # Verify no error logging occurred
        mock_logger.error.assert_not_called()

    @patch("survey_studio.retry.logger")
    def test_retry_arxiv_success_after_failures(self, mock_logger: Mock) -> None:  # noqa: ARG002
        """Test successful operation after initial failures."""
        call_count = 0

        @retry_arxiv_operations
        def test_function() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < EXPECTED_RETRY_ATTEMPTS:
                raise ConnectionError("Network error")
            return "success"

        result = test_function()
        assert result == "success"
        assert call_count == EXPECTED_RETRY_ATTEMPTS

    @patch("survey_studio.retry.logger")
    def test_retry_arxiv_final_failure(self, mock_logger: Mock) -> None:  # noqa: ARG002
        """Test final failure after all retry attempts."""

        @retry_arxiv_operations
        def test_function() -> str:
            raise ConnectionError("Persistent network error")

        with pytest.raises(ExternalServiceError) as exc_info:
            test_function()

        assert "arXiv operation failed" in str(exc_info.value)
        assert exc_info.value.context["service"] == "arXiv"

    @patch("survey_studio.retry.logger")
    def test_retry_llm_rate_limit_handling(self, mock_logger: Mock) -> None:  # noqa: ARG002
        """Test LLM retry with rate limit errors."""
        call_count = 0

        @retry_llm_operations
        def test_function() -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise LLMError("Rate limit exceeded", model="gpt-4o-mini")
            return "success"

        result = test_function()
        assert result == "success"
        assert call_count == EXPECTED_RETRY_ATTEMPTS_2

    @patch("survey_studio.retry.logger")
    def test_retry_export_file_operations(self, mock_logger: Mock) -> None:  # noqa: ARG002
        """Test export retry with file operation errors."""
        call_count = 0

        @retry_export_operations
        def test_function() -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise OSError("File system error")
            return "success"

        result = test_function()
        assert result == "success"
        assert call_count == EXPECTED_RETRY_ATTEMPTS_2

    @patch("survey_studio.retry.logger")
    def test_no_retry_on_validation_error(self, mock_logger: Mock) -> None:  # noqa: ARG002
        """Test that validation errors are not retried."""
        call_count = 0

        @retry_arxiv_operations
        def test_function() -> str:
            nonlocal call_count
            call_count += 1
            raise ValidationError("Invalid input")

        with pytest.raises(ValidationError):
            test_function()

        # Should not retry validation errors
        assert call_count == 1
        # Verify no retry logging occurred
        mock_logger.warning.assert_not_called()

    @patch("survey_studio.retry.logger")
    def test_no_retry_on_configuration_error(self, mock_logger: Mock) -> None:  # noqa: ARG002
        """Test that configuration errors are not retried."""
        call_count = 0

        @retry_llm_operations
        def test_function() -> str:
            nonlocal call_count
            call_count += 1
            raise ConfigurationError("Missing API key")

        with pytest.raises(ConfigurationError):
            test_function()

        # Should not retry configuration errors
        assert call_count == 1
        # Verify no retry logging occurred
        mock_logger.warning.assert_not_called()


class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    def setUp(self) -> None:
        """Reset circuit breakers before each test."""
        reset_circuit_breaker("test_service")

    def test_circuit_breaker_normal_operation(self) -> None:
        """Test circuit breaker allows normal operations."""

        @circuit_breaker("test_service")
        def test_function() -> str:
            return "success"

        result = test_function()
        assert result == "success"

    def test_circuit_breaker_opens_after_failures(self) -> None:
        """Test circuit breaker opens after consecutive failures."""

        @circuit_breaker("test_service")
        def test_function() -> str:
            raise ConnectionError("Persistent error")

        # Should fail 5 times before circuit opens
        for _ in range(5):
            with pytest.raises(ConnectionError):
                test_function()

        # Circuit should now be open
        status = get_circuit_breaker_status()
        assert status["test_service"]["is_open"]
        assert status["test_service"]["failure_count"] >= CIRCUIT_BREAKER_THRESHOLD

    def test_circuit_breaker_prevents_calls_when_open(self) -> None:
        """Test circuit breaker prevents calls when open."""
        # Manually set circuit to open
        from survey_studio.retry import _circuit_state

        _circuit_state["test_service"]["is_open"] = True
        _circuit_state["test_service"]["failure_count"] = 10
        _circuit_state["test_service"]["last_failure_time"] = time.time()

        @circuit_breaker("test_service")
        def test_function() -> str:
            return "should not be called"

        with pytest.raises(ExternalServiceError) as exc_info:
            test_function()

        assert "Circuit breaker is open" in str(exc_info.value)

    def test_circuit_breaker_recovery(self) -> None:
        """Test circuit breaker recovery after timeout."""
        # Set circuit to open but with old timestamp
        from survey_studio.retry import _circuit_state

        _circuit_state["test_service"]["is_open"] = True
        _circuit_state["test_service"]["failure_count"] = 5
        # 6+ minutes ago
        _circuit_state["test_service"]["last_failure_time"] = time.time() - 400

        @circuit_breaker("test_service")
        def test_function() -> str:
            return "recovered"

        result = test_function()
        assert result == "recovered"

        # Circuit should be closed again
        status = get_circuit_breaker_status()
        assert not status["test_service"]["is_open"]

    def test_circuit_breaker_status_tracking(self) -> None:
        """Test circuit breaker status tracking."""
        # Initially should be closed
        status = get_circuit_breaker_status()
        assert not status.get("test_service", {}).get("is_open", False)

        # Manually update circuit breaker state
        _update_circuit_breaker("test_service", success=False)
        _update_circuit_breaker("test_service", success=False)

        status = get_circuit_breaker_status()
        assert status["test_service"]["failure_count"] == EXPECTED_RETRY_ATTEMPTS_2
        # Not open yet (threshold is 5)
        assert not status["test_service"]["is_open"]

        # Reset should clear state
        reset_circuit_breaker("test_service")
        status = get_circuit_breaker_status()
        assert status["test_service"]["failure_count"] == 0


class TestExceptionClassification:
    """Test exception classification for retry decisions."""

    def test_should_retry_network_errors(self) -> None:
        """Test that network errors should be retried."""
        assert _should_retry_exception(ConnectionError("Network down"))
        assert _should_retry_exception(TimeoutError("Request timeout"))

    def test_should_retry_external_service_errors(self) -> None:
        """Test that external service errors should be retried."""
        arxiv_error = ExternalServiceError("arXiv down", service="arXiv")
        llm_error = LLMError("OpenAI rate limit", model="gpt-4o-mini")
        export_error = ExportError("File system full", format_type="pdf")

        assert _should_retry_exception(arxiv_error)
        assert _should_retry_exception(llm_error)
        assert _should_retry_exception(export_error)

    def test_should_not_retry_validation_errors(self) -> None:
        """Test that validation errors should not be retried."""
        validation_error = ValidationError("Invalid input", field="query")
        config_error = ConfigurationError("Missing API key")

        assert not _should_retry_exception(validation_error)
        assert not _should_retry_exception(config_error)

    def test_should_retry_http_5xx_errors(self) -> None:
        """Test that HTTP 5xx errors should be retried."""
        # Mock HTTP error with 5xx status code
        http_error = Mock()
        http_error.response = Mock()
        http_error.response.status_code = 503

        assert _should_retry_exception(http_error)

    def test_should_not_retry_http_4xx_errors(self) -> None:
        """Test that HTTP 4xx errors should not be retried."""
        # Mock HTTP error with 4xx status code
        http_error = Mock()
        http_error.response = Mock()
        http_error.response.status_code = 404

        assert not _should_retry_exception(http_error)

    def test_unknown_exception_not_retried(self) -> None:
        """Test that unknown exceptions are not retried by default."""
        unknown_error = RuntimeError("Unknown error")

        assert not _should_retry_exception(unknown_error)


class TestCircuitBreakerHelpers:
    """Test circuit breaker helper functions."""

    def test_check_circuit_breaker_closed(self) -> None:
        """Test circuit breaker check when closed."""
        reset_circuit_breaker("test_service")

        # Should not raise when circuit is closed
        _check_circuit_breaker("test_service")

    def test_check_circuit_breaker_open(self) -> None:
        """Test circuit breaker check when open."""
        # Manually open circuit
        from survey_studio.retry import _circuit_state

        _circuit_state["test_service"]["is_open"] = True
        _circuit_state["test_service"]["failure_count"] = 10
        _circuit_state["test_service"]["last_failure_time"] = time.time()

        with pytest.raises(ExternalServiceError) as exc_info:
            _check_circuit_breaker("test_service")

        assert "Circuit breaker is open" in str(exc_info.value)
        assert exc_info.value.context["service"] == "test_service"

    def test_update_circuit_breaker_success(self) -> None:
        """Test circuit breaker update on success."""
        # Set some initial failures
        _update_circuit_breaker("test_service", success=False)
        _update_circuit_breaker("test_service", success=False)

        status = get_circuit_breaker_status()
        assert status["test_service"]["failure_count"] == EXPECTED_RETRY_ATTEMPTS_2

        # Success should reset
        _update_circuit_breaker("test_service", success=True)

        status = get_circuit_breaker_status()
        assert status["test_service"]["failure_count"] == 0
        assert not status["test_service"]["is_open"]

    def test_update_circuit_breaker_failure(self) -> None:
        """Test circuit breaker update on failure."""
        reset_circuit_breaker("test_service")

        # Add failures one by one
        for i in range(1, 6):  # 5 failures to open circuit
            _update_circuit_breaker("test_service", success=False)
            status = get_circuit_breaker_status()

            if i < CIRCUIT_BREAKER_THRESHOLD:
                assert not status["test_service"]["is_open"]
            else:
                assert status["test_service"]["is_open"]


class TestRetryExceptionHandling:
    """Test exception handling in retry logic."""

    def test_should_retry_exception_handling(self) -> None:
        """Test should_retry handles exceptions in context checking."""

        # Create a mock exception that raises when accessing context
        class ProblematicError(ExternalServiceError):
            def __init__(self, message: str, service: str) -> None:
                # Don't call super().__init__ to avoid the context attribute issue
                Exception.__init__(self, message)
                self.message = message
                self.service = service
                self._context = {"no_retry": True}

            def __getattr__(self, name: str) -> Any:
                if name == "context":
                    raise RuntimeError("Context access failed")
                raise AttributeError(
                    f"'{self.__class__.__name__}' object has no attribute '{name}'"
                )

        exc = ProblematicError("Test error", "test")

        # Should still retry because it's an ExternalServiceError,
        # even though context access fails
        # The exception handling in the function catches the RuntimeError and continues
        assert _should_retry_exception(exc)

    def test_log_retry_attempt_with_exception(self) -> None:
        """Test _log_retry_attempt logs warning with exception details."""
        with patch("survey_studio.retry.with_context") as mock_with_context:
            mock_logger = Mock()
            mock_with_context.return_value = mock_logger

            # Create a mock retry state with exception
            retry_state = Mock()
            retry_state.attempt_number = 2
            retry_state.outcome = Mock()
            retry_state.outcome.exception.return_value = ValueError("Test error")

            _log_retry_attempt(retry_state)

            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args
            assert "Retry attempt 2 failed" in call_args[0][0]
            assert (
                call_args[1]["extra"]["extra_fields"]["attempt"]
                == EXPECTED_ATTEMPT_NUMBER
            )
            assert (
                call_args[1]["extra"]["extra_fields"]["exception_type"] == "ValueError"
            )

    def test_log_retry_attempt_without_exception(self) -> None:
        """Test _log_retry_attempt doesn't log when there's no exception."""
        with patch("survey_studio.retry.with_context") as mock_with_context:
            mock_logger = Mock()
            mock_with_context.return_value = mock_logger

            # Create a mock retry state without exception
            retry_state = Mock()
            retry_state.attempt_number = 1
            retry_state.outcome = None

            _log_retry_attempt(retry_state)

            # Should not log anything when there's no exception
            mock_logger.warning.assert_not_called()
            mock_logger.info.assert_not_called()


@pytest.fixture(autouse=True)
def _cleanup_circuit_breakers() -> Generator[None, None, None]:
    """Clean up circuit breakers after each test."""
    yield
    # Reset test service circuit breaker
    reset_circuit_breaker("test_service")
