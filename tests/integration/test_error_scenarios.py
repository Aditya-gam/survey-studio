"""Integration tests for error handling scenarios.

Tests timeout scenarios, 5xx errors, configuration errors, and logging security
across the application components.
"""

from __future__ import annotations

import logging
import os
import time
from typing import TYPE_CHECKING, Any
from unittest.mock import Mock, patch

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator

from survey_studio.agents import build_team, make_llm_client
from survey_studio.errors import (
    ConfigurationError,
    ExternalServiceError,
    LLMError,
    get_error_details,
    get_user_friendly_message,
)
from survey_studio.logging import (
    configure_logging,
    log_error_with_details,
    new_session_id,
    redact_sensitive_data,
    set_session_id,
)
from survey_studio.retry import (
    get_circuit_breaker_status,
    reset_circuit_breaker,
)
from survey_studio.tools import arxiv_search

# Test constants
EXPECTED_RETRY_ATTEMPTS = 3
EXPECTED_CLIENT_CALLS = 2
EXPECTED_RETRY_ATTEMPTS_2 = 2
MAX_FIELD_LENGTH = 1015
CIRCUIT_BREAKER_THRESHOLD = 5
EXPECTED_TOKEN_COUNT = 1000


class TestTimeoutScenarios:
    """Test timeout handling across different services."""

    @pytest.fixture(autouse=True)
    def _setup_logging(self) -> None:
        """Set up logging for tests."""
        configure_logging(level=logging.DEBUG)
        set_session_id(new_session_id())

    def test_arxiv_timeout_scenario(self) -> None:
        """Test arXiv API timeout with retry behavior."""
        with patch("arxiv.Client") as mock_client_class:
            # Mock client that raises timeout on first calls, succeeds on last
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            # First two calls raise timeout, third succeeds
            mock_client.results.side_effect = [
                TimeoutError("arXiv API timeout"),
                TimeoutError("arXiv API timeout"),
                [self._create_mock_arxiv_result()],
            ]

            # Should eventually succeed after retries
            results = arxiv_search("machine learning", max_results=1)

            assert len(results) == 1
            assert results[0]["title"] == "Test Paper"
            assert mock_client.results.call_count == EXPECTED_RETRY_ATTEMPTS

    def test_arxiv_permanent_timeout(self) -> None:
        """Test arXiv API permanent timeout causing final failure."""
        with patch("arxiv.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            # All calls raise timeout
            mock_client.results.side_effect = TimeoutError("arXiv API timeout")

            # Should raise ExternalServiceError after retries
            with pytest.raises(ExternalServiceError) as exc_info:
                arxiv_search("machine learning", max_results=1)

            assert "arXiv" in str(exc_info.value)
            assert exc_info.value.context["service"] == "arXiv"

    def test_llm_timeout_scenario(self) -> None:
        """Test LLM API timeout with retry behavior."""
        with patch(
            "survey_studio.agents.OpenAIChatCompletionClient"
        ) as mock_client_class:
            # First call raises timeout, second succeeds
            mock_client_class.side_effect = [TimeoutError("OpenAI API timeout"), Mock()]

            # Should eventually succeed after retry
            client = make_llm_client("gpt-4o-mini", "test-key")

            assert client is not None
            assert mock_client_class.call_count == EXPECTED_CLIENT_CALLS

    def _create_mock_arxiv_result(self) -> Mock:
        """Create a mock arXiv result."""
        result = Mock()
        result.title = "Test Paper"
        result.authors = [Mock(name="Test Author")]
        result.published = Mock()
        result.published.strftime.return_value = "2023-01-01"
        result.summary = "Test summary"
        result.pdf_url = "http://test.pdf"
        result.entry_id = "test-id"
        result.categories = ["cs.LG"]
        return result


class TestHTTPErrorScenarios:
    """Test 5xx HTTP error scenarios."""

    @pytest.fixture(autouse=True)
    def _setup_logging(self) -> None:
        """Set up logging for tests."""
        configure_logging(level=logging.DEBUG)
        set_session_id(new_session_id())

    def test_arxiv_500_error_retry(self) -> None:
        """Test arXiv API 500 error with retry behavior."""
        with patch("arxiv.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            # First call raises 500 error, second succeeds
            http_error = Exception("HTTP 500: Internal Server Error")
            mock_client.results.side_effect = [
                http_error,
                [self._create_mock_arxiv_result()],
            ]

            # Should eventually succeed after retry
            results = arxiv_search("quantum computing", max_results=1)

            assert len(results) == 1
            assert mock_client.results.call_count == EXPECTED_RETRY_ATTEMPTS_2

    def test_arxiv_503_service_unavailable(self) -> None:
        """Test arXiv API 503 service unavailable."""
        with patch("arxiv.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            # All calls raise 503 error
            http_error = Exception("HTTP 503: Service Unavailable")
            mock_client.results.side_effect = http_error

            # Should raise ExternalServiceError after retries
            with pytest.raises(ExternalServiceError) as exc_info:
                arxiv_search("quantum computing", max_results=1)

            assert "arXiv" in str(exc_info.value)
            assert exc_info.value.severity.value == "warning"

    def _create_mock_arxiv_result(self) -> Mock:
        """Create a mock arXiv result."""
        result = Mock()
        result.title = "Quantum Test Paper"
        result.authors = [Mock(name="Quantum Author")]
        result.published = Mock()
        result.published.strftime.return_value = "2023-01-01"
        result.summary = "Quantum test summary"
        result.pdf_url = "http://quantum-test.pdf"
        result.entry_id = "quantum-test-id"
        result.categories = ["quant-ph"]
        return result


class TestConfigurationErrors:
    """Test configuration error scenarios."""

    def test_missing_api_key(self) -> None:
        """Test missing OpenAI API key configuration."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ConfigurationError) as exc_info:
                build_team("gpt-4o-mini")

            assert "OpenAI API key not found" in str(exc_info.value)
            assert exc_info.value.context["missing_env_var"] == "OPENAI_API_KEY"

    def test_invalid_model_name(self) -> None:
        """Test invalid model name configuration."""
        with pytest.raises(ConfigurationError) as exc_info:
            make_llm_client("", "test-key")

        assert "Model name cannot be empty" in str(exc_info.value)

    def test_empty_api_key(self) -> None:
        """Test empty API key configuration."""
        with pytest.raises(ConfigurationError) as exc_info:
            make_llm_client("gpt-4o-mini", "")

        assert "API key cannot be empty" in str(exc_info.value)


class TestLoggingSecurity:
    """Test logging security and sensitive data redaction."""

    def test_api_key_redaction(self) -> None:
        """Test that API keys are redacted from logs."""
        sensitive_data = {
            "api_key": "sk-1234567890abcdef",  # pragma: allowlist secret
            "openai_api_key": "sk-abcdef1234567890",  # pragma: allowlist secret
            "authorization": "Bearer token123",
            "normal_field": "safe_value",
        }

        redacted = redact_sensitive_data(sensitive_data)

        assert redacted["api_key"] == "***REDACTED***"
        assert redacted["openai_api_key"] == "***REDACTED***"
        assert redacted["authorization"] == "***REDACTED***"
        assert redacted["normal_field"] == "safe_value"

    def test_password_redaction(self) -> None:
        """Test that passwords are redacted from logs."""
        sensitive_data = {
            "password": "secret123",  # pragma: allowlist secret
            "passwd": "secret456",  # pragma: allowlist secret
            "secret": "confidential",  # pragma: allowlist secret
            "user": "john_doe",
        }

        redacted = redact_sensitive_data(sensitive_data)

        assert redacted["password"] == "***REDACTED***"
        assert redacted["passwd"] == "***REDACTED***"
        assert redacted["secret"] == "***REDACTED***"
        assert redacted["user"] == "john_doe"

    def test_long_value_truncation(self) -> None:
        """Test that long values are truncated in logs."""
        long_value = "x" * 1500  # Longer than MAX_LOG_VALUE_LENGTH (1000)
        data = {"long_field": long_value}

        redacted = redact_sensitive_data(data)

        assert len(redacted["long_field"]) <= MAX_FIELD_LENGTH
        assert redacted["long_field"].endswith("...[TRUNCATED]")

    def test_regex_pattern_redaction(self) -> None:
        """Test that regex patterns catch sensitive data."""
        sensitive_text = "api_key=sk-1234567890 and token: bearer_xyz123"
        data = {"message": sensitive_text}

        redacted = redact_sensitive_data(data)

        assert "sk-1234567890" not in redacted["message"]
        assert "***REDACTED***" in redacted["message"]

    def test_structured_error_logging(self, caplog: Any) -> None:
        """Test structured error logging with redaction."""
        logger = logging.getLogger(__name__)

        # Create error with sensitive context
        error = ExternalServiceError(
            "API call failed",
            service="TestService",
            context={
                "api_key": "sk-secret123",  # pragma: allowlist secret
                "endpoint": "/api/test",
                "user_id": "user123",
            },
        )

        with caplog.at_level(logging.ERROR):
            log_error_with_details(
                logger,
                error,
                "test_operation",
                "test_component",
                additional_secret="password123",  # pragma: allowlist secret
            )

        # Check that log was created and sensitive data is redacted
        assert len(caplog.records) == 1
        log_record = caplog.records[0]
        assert "API call failed" in log_record.getMessage()

        # Check that sensitive data is not in the log output
        log_output = str(log_record.__dict__)
        assert "sk-secret123" not in log_output
        assert "password123" not in log_output


class TestCircuitBreaker:
    """Test circuit breaker behavior."""

    def setUp(self) -> None:
        """Reset circuit breakers before each test."""
        # Reset all circuit breakers
        for service in ["arXiv", "LLM", "export"]:
            reset_circuit_breaker(service)

    def test_circuit_breaker_opens_after_failures(self) -> None:
        """Test that circuit breaker opens after consecutive failures."""
        with patch("arxiv.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.results.side_effect = Exception("Persistent failure")

            # Should fail 5 times before circuit opens
            for _ in range(5):
                with pytest.raises(ExternalServiceError):
                    arxiv_search("test", max_results=1)

            # Circuit breaker should now be open
            status = get_circuit_breaker_status()
            assert status["arXiv"]["is_open"]
            assert status["arXiv"]["failure_count"] >= CIRCUIT_BREAKER_THRESHOLD

    def test_circuit_breaker_prevents_calls_when_open(self) -> None:
        """Test that circuit breaker prevents calls when open."""
        # Manually open the circuit breaker
        from survey_studio.retry import _circuit_state

        _circuit_state["arXiv"]["is_open"] = True
        _circuit_state["arXiv"]["failure_count"] = 10
        _circuit_state["arXiv"]["last_failure_time"] = time.time()

        # Should raise ExternalServiceError immediately without trying the call
        with pytest.raises(ExternalServiceError) as exc_info:
            arxiv_search("test", max_results=1)

        assert "Circuit breaker is open" in str(exc_info.value)

    def test_circuit_breaker_recovery(self) -> None:
        """Test circuit breaker recovery after timeout."""
        # Set up circuit breaker that should recover
        from survey_studio.retry import _circuit_state

        _circuit_state["arXiv"]["is_open"] = True
        _circuit_state["arXiv"]["failure_count"] = 5
        _circuit_state["arXiv"]["last_failure_time"] = (
            time.time() - 400
        )  # 6+ minutes ago

        with patch("arxiv.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.results.return_value = [self._create_mock_arxiv_result()]

            # Should succeed as circuit breaker recovers
            results = arxiv_search("test", max_results=1)

            assert len(results) == 1

            # Circuit breaker should be closed
            status = get_circuit_breaker_status()
            assert not status["arXiv"]["is_open"]

    def _create_mock_arxiv_result(self) -> Mock:
        """Create a mock arXiv result."""
        result = Mock()
        result.title = "Circuit Test Paper"
        result.authors = [Mock(name="Circuit Author")]
        result.published = Mock()
        result.published.strftime.return_value = "2023-01-01"
        result.summary = "Circuit test summary"
        result.pdf_url = "http://circuit-test.pdf"
        result.entry_id = "circuit-test-id"
        result.categories = ["cs.LG"]
        return result


class TestErrorMapping:
    """Test error mapping and user-friendly messages."""

    def test_survey_studio_error_mapping(self) -> None:
        """Test mapping of SurveyStudioError to user-friendly messages."""
        error = ExternalServiceError("HTTP 503 Service Unavailable", service="arXiv")

        user_message = get_user_friendly_message(error)
        assert "arXiv service is temporarily unavailable" in user_message
        assert "try again in a few moments" in user_message

    def test_standard_exception_mapping(self) -> None:
        """Test mapping of standard Python exceptions."""
        timeout_error = TimeoutError("Connection timed out")
        user_message = get_user_friendly_message(timeout_error)
        assert "Request timed out" in user_message

        connection_error = ConnectionError("Failed to connect")
        user_message = get_user_friendly_message(connection_error)
        assert "Network connection failed" in user_message

    def test_unknown_exception_mapping(self) -> None:
        """Test mapping of unknown exceptions."""
        unknown_error = RuntimeError("Unknown error")
        user_message = get_user_friendly_message(unknown_error)
        assert "unexpected error occurred" in user_message

    def test_error_details_extraction(self) -> None:
        """Test extraction of structured error details."""
        error = LLMError("Model failed", model="gpt-4o-mini", context={"tokens": 1000})

        details = get_error_details(error)

        assert details["type"] == "LLMError"
        assert details["message"] == "Model failed"
        assert details["error_id"] == error.error_id
        assert details["severity"] == "error"
        assert details["context"]["model"] == "gpt-4o-mini"
        assert details["context"]["tokens"] == EXPECTED_TOKEN_COUNT


@pytest.fixture(autouse=True)
def _cleanup_circuit_breakers() -> Generator[None, None, None]:
    """Clean up circuit breakers after each test."""
    yield
    # Reset all circuit breakers after each test
    for service in ["arXiv", "LLM", "export"]:
        reset_circuit_breaker(service)
