"""Unit tests for errors.py module."""

from __future__ import annotations

import pytest

from survey_studio.errors import (
    AgentCreationError,
    ArxivSearchError,
    OrchestrationError,
    SurveyStudioError,
    ValidationError,
)


class TestExceptionHierarchy:
    """Test exception class hierarchy and inheritance."""

    def test_base_exception_inheritance(self) -> None:
        """Test SurveyStudioError inherits from Exception."""
        assert issubclass(SurveyStudioError, Exception)

    def test_arxiv_search_error_inheritance(self) -> None:
        """Test ArxivSearchError inherits from SurveyStudioError."""
        assert issubclass(ArxivSearchError, SurveyStudioError)
        assert issubclass(ArxivSearchError, Exception)

    def test_agent_creation_error_inheritance(self) -> None:
        """Test AgentCreationError inherits from SurveyStudioError."""
        assert issubclass(AgentCreationError, SurveyStudioError)
        assert issubclass(AgentCreationError, Exception)

    def test_validation_error_inheritance(self) -> None:
        """Test ValidationError inherits from SurveyStudioError."""
        assert issubclass(ValidationError, SurveyStudioError)
        assert issubclass(ValidationError, Exception)

    def test_orchestration_error_inheritance(self) -> None:
        """Test OrchestrationError inherits from SurveyStudioError."""
        assert issubclass(OrchestrationError, SurveyStudioError)
        assert issubclass(OrchestrationError, Exception)


class TestSurveyStudioError:
    """Test SurveyStudioError base class."""

    def test_default_message(self) -> None:
        """Test default error message."""
        error = SurveyStudioError()
        assert str(error) == ""

    def test_custom_message(self) -> None:
        """Test custom error message."""
        message = "Test error message"
        error = SurveyStudioError(message)
        assert str(error) == message

    def test_exception_instantiation(self) -> None:
        """Test exception can be instantiated and raised."""
        with pytest.raises(SurveyStudioError):
            raise SurveyStudioError("Test message")


class TestArxivSearchError:
    """Test ArxivSearchError exception."""

    def test_default_message(self) -> None:
        """Test default error message."""
        error = ArxivSearchError()
        assert str(error) == ""

    def test_custom_message(self) -> None:
        """Test custom error message."""
        message = "Failed to search arXiv"
        error = ArxivSearchError(message)
        assert str(error) == message

    def test_exception_type(self) -> None:
        """Test exception is correct type."""
        error = ArxivSearchError("Test")
        assert isinstance(error, ArxivSearchError)
        assert isinstance(error, SurveyStudioError)
        assert isinstance(error, Exception)

    def test_exception_instantiation_and_raise(self) -> None:
        """Test exception can be instantiated and raised."""
        with pytest.raises(ArxivSearchError):
            raise ArxivSearchError("Test arXiv error")


class TestAgentCreationError:
    """Test AgentCreationError exception."""

    def test_default_message(self) -> None:
        """Test default error message."""
        error = AgentCreationError()
        assert str(error) == ""

    def test_custom_message(self) -> None:
        """Test custom error message."""
        message = "Failed to create agent"
        error = AgentCreationError(message)
        assert str(error) == message

    def test_exception_type(self) -> None:
        """Test exception is correct type."""
        error = AgentCreationError("Test")
        assert isinstance(error, AgentCreationError)
        assert isinstance(error, SurveyStudioError)
        assert isinstance(error, Exception)

    def test_exception_instantiation_and_raise(self) -> None:
        """Test exception can be instantiated and raised."""
        with pytest.raises(AgentCreationError):
            raise AgentCreationError("Test agent creation error")


class TestValidationError:
    """Test ValidationError exception."""

    def test_default_message(self) -> None:
        """Test default error message."""
        error = ValidationError()
        assert str(error) == ""

    def test_custom_message(self) -> None:
        """Test custom error message."""
        message = "Invalid input provided"
        error = ValidationError(message)
        assert str(error) == message

    def test_exception_type(self) -> None:
        """Test exception is correct type."""
        error = ValidationError("Test")
        assert isinstance(error, ValidationError)
        assert isinstance(error, SurveyStudioError)
        assert isinstance(error, Exception)

    def test_exception_instantiation_and_raise(self) -> None:
        """Test exception can be instantiated and raised."""
        with pytest.raises(ValidationError):
            raise ValidationError("Test validation error")


class TestOrchestrationError:
    """Test OrchestrationError exception."""

    def test_default_message(self) -> None:
        """Test default error message."""
        error = OrchestrationError()
        assert str(error) == ""

    def test_custom_message(self) -> None:
        """Test custom error message."""
        message = "Orchestration failed"
        error = OrchestrationError(message)
        assert str(error) == message

    def test_exception_type(self) -> None:
        """Test exception is correct type."""
        error = OrchestrationError("Test")
        assert isinstance(error, OrchestrationError)
        assert isinstance(error, SurveyStudioError)
        assert isinstance(error, Exception)

    def test_exception_instantiation_and_raise(self) -> None:
        """Test exception can be instantiated and raised."""
        with pytest.raises(OrchestrationError):
            raise OrchestrationError("Test orchestration error")


class TestExceptionChaining:
    """Test exception chaining and context preservation."""

    def test_exception_chaining(self) -> None:
        """Test exception chaining with __cause__."""
        original_error = ValueError("Original error")
        chained_error = SurveyStudioError("Chained error")

        with pytest.raises(SurveyStudioError) as exc_info:
            raise chained_error from original_error

        assert exc_info.value.__cause__ is original_error
        assert isinstance(exc_info.value.__cause__, ValueError)

    def test_arxiv_error_chaining(self) -> None:
        """Test ArxivSearchError chaining."""
        original_error = ConnectionError("Network error")
        chained_error = ArxivSearchError("Search failed")

        with pytest.raises(ArxivSearchError) as exc_info:
            raise chained_error from original_error

        assert exc_info.value.__cause__ is original_error
        assert isinstance(exc_info.value.__cause__, ConnectionError)

    def test_agent_error_chaining(self) -> None:
        """Test AgentCreationError chaining."""
        original_error = ImportError("Missing dependency")
        chained_error = AgentCreationError("Agent creation failed")

        with pytest.raises(AgentCreationError) as exc_info:
            raise chained_error from original_error

        assert exc_info.value.__cause__ is original_error
        assert isinstance(exc_info.value.__cause__, ImportError)

    def test_validation_error_chaining(self) -> None:
        """Test ValidationError chaining."""
        original_error = TypeError("Wrong type")
        chained_error = ValidationError("Validation failed")

        with pytest.raises(ValidationError) as exc_info:
            raise chained_error from original_error

        assert exc_info.value.__cause__ is original_error
        assert isinstance(exc_info.value.__cause__, TypeError)

    def test_orchestration_error_chaining(self) -> None:
        """Test OrchestrationError chaining."""
        original_error = RuntimeError("Runtime failure")
        chained_error = OrchestrationError("Orchestration failed")

        with pytest.raises(OrchestrationError) as exc_info:
            raise chained_error from original_error

        assert exc_info.value.__cause__ is original_error
        assert isinstance(exc_info.value.__cause__, RuntimeError)


class TestExceptionContext:
    """Test exception context and traceback preservation."""

    def test_exception_context_preservation(self) -> None:
        """Test exception context is preserved."""

        def _raise_nested_error() -> None:
            try:
                raise ValueError("Inner error")
            except ValueError:
                raise SurveyStudioError("Outer error") from None

        with pytest.raises(SurveyStudioError) as exc_info:
            _raise_nested_error()

        assert exc_info.value.__context__ is not None
        assert isinstance(exc_info.value.__context__, ValueError)

    def test_traceback_preservation(self) -> None:
        """Test traceback is preserved."""
        with pytest.raises(ArxivSearchError) as exc_info:
            raise ArxivSearchError("Test error")

        assert exc_info.value.__traceback__ is not None


class TestExceptionProperties:
    """Test custom exception properties and methods."""

    def test_exception_has_args(self) -> None:
        """Test exceptions have args attribute."""
        error = SurveyStudioError("Test message")
        assert error.args == ("Test message",)

    def test_exception_empty_args(self) -> None:
        """Test exceptions with no message have empty args."""
        error = SurveyStudioError()
        assert error.args == ()

    def test_exception_str_method(self) -> None:
        """Test exception string representation."""
        error = ValidationError("Test validation")
        assert str(error) == "Test validation"
        assert repr(error) == "ValidationError('Test validation')"
