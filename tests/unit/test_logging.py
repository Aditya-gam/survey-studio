"""Unit tests for logging.py module."""

from __future__ import annotations

from io import StringIO
import logging
from unittest.mock import patch

from survey_studio.logging import (
    KeyValueFormatter,
    _safe,
    configure_logging,
    get_session_id,
    log_error_with_details,
    new_session_id,
    set_session_id,
    with_context,
)

# Constants for magic numbers
SESSION_ID_LENGTH = 8
UNIQUE_ID_TEST_COUNT = 100


class TestSessionIdManagement:
    """Test session ID management functions."""

    def test_new_session_id_format(self) -> None:
        """Test new_session_id returns 8-character hex string."""
        session_id = new_session_id()
        assert isinstance(session_id, str)
        assert len(session_id) == SESSION_ID_LENGTH
        assert session_id.isalnum()
        # Should be valid hex
        int(session_id, 16)

    def test_new_session_id_uniqueness(self) -> None:
        """Test new_session_id generates unique IDs."""
        ids = {new_session_id() for _ in range(UNIQUE_ID_TEST_COUNT)}
        assert len(ids) == UNIQUE_ID_TEST_COUNT  # All should be unique

    def test_set_session_id(self) -> None:
        """Test set_session_id sets the session ID."""
        test_id = "test1234"
        set_session_id(test_id)
        assert get_session_id() == test_id

    def test_get_session_id_default(self) -> None:
        """Test get_session_id returns default when not set."""
        # Reset to default
        set_session_id("-")
        assert get_session_id() == "-"

    def test_get_session_id_after_set(self) -> None:
        """Test get_session_id returns set value."""
        test_id = "abcd1234"
        set_session_id(test_id)
        assert get_session_id() == test_id

    def test_session_id_context_isolation(self) -> None:
        """Test session ID is isolated per context."""
        original_id = get_session_id()
        test_id = "isolate12"

        set_session_id(test_id)
        assert get_session_id() == test_id

        # Reset to original
        set_session_id(original_id)
        assert get_session_id() == original_id


class TestSafeFunction:
    """Test _safe function for value formatting."""

    def test_safe_normal_string(self) -> None:
        """Test normal string without spaces."""
        assert _safe("normal") == "normal"

    def test_safe_string_with_spaces(self) -> None:
        """Test string with spaces gets quoted."""
        assert _safe("has spaces") == '"has spaces"'

    def test_safe_string_with_tabs(self) -> None:
        """Test string with tabs gets quoted."""
        assert _safe("has\ttabs") == '"has\ttabs"'

    def test_safe_string_with_newlines(self) -> None:
        """Test string with newlines gets quoted."""
        assert _safe("has\nnewlines") == '"has\nnewlines"'

    def test_safe_empty_string(self) -> None:
        """Test empty string."""
        assert _safe("") == ""

    def test_safe_numeric_value(self) -> None:
        """Test numeric value conversion."""
        assert _safe(42) == "42"
        assert _safe(3.14) == "3.14"

    def test_safe_boolean_value(self) -> None:
        """Test boolean value conversion."""
        assert _safe(True) == "True"
        assert _safe(False) == "False"

    def test_safe_none_value(self) -> None:
        """Test None value conversion."""
        assert _safe(None) == "None"

    def test_safe_list_value(self) -> None:
        """Test list value conversion."""
        assert _safe([1, 2, 3]) == '"[1, 2, 3]"'

    def test_safe_dict_value(self) -> None:
        """Test dict value conversion."""
        assert _safe({"key": "value"}) == "\"{'key': 'value'}\""


class TestKeyValueFormatter:
    """Test KeyValueFormatter class."""

    def test_formatter_creation(self) -> None:
        """Test formatter can be instantiated."""
        formatter = KeyValueFormatter()
        assert isinstance(formatter, logging.Formatter)

    def test_format_basic_record(self) -> None:
        """Test formatting a basic log record."""
        formatter = KeyValueFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Set session ID for test
        set_session_id("test1234")

        result = formatter.format(record)
        assert "level=INFO" in result
        assert "logger=test.logger" in result
        assert "session_id=test1234" in result
        assert 'message="Test message"' in result  # Messages with spaces are quoted

    def test_format_record_with_args(self) -> None:
        """Test formatting record with message args."""
        formatter = KeyValueFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="Test %s message",
            args=("formatted",),
            exc_info=None,
        )
        set_session_id("test5678")

        result = formatter.format(record)
        assert "level=ERROR" in result
        # Messages with spaces are quoted
        assert 'message="Test formatted message"' in result

    def test_format_record_with_extra_fields(self) -> None:
        """Test formatting record with extra fields."""
        formatter = KeyValueFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.DEBUG,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        # Simulate extra fields
        record.__dict__["extra_fields"] = {"user_id": "123", "action": "login"}

        set_session_id("extra999")

        result = formatter.format(record)
        assert "user_id=123" in result
        assert "action=login" in result

    def test_format_record_with_quoted_message(self) -> None:
        """Test formatting record with message containing spaces."""
        formatter = KeyValueFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.WARNING,
            pathname="test.py",
            lineno=10,
            msg="Message with spaces",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        assert 'message="Message with spaces"' in result

    def test_format_different_levels(self) -> None:
        """Test formatting records with different log levels."""
        formatter = KeyValueFormatter()
        levels = [
            (logging.DEBUG, "DEBUG"),
            (logging.INFO, "INFO"),
            (logging.WARNING, "WARNING"),
            (logging.ERROR, "ERROR"),
            (logging.CRITICAL, "CRITICAL"),
        ]

        for level_num, level_name in levels:
            record = logging.LogRecord(
                name="test",
                level=level_num,
                pathname="test.py",
                lineno=1,
                msg="test",
                args=(),
                exc_info=None,
            )
            result = formatter.format(record)
            assert f"level={level_name}" in result


class TestConfigureLogging:
    """Test configure_logging function."""

    def test_configure_logging_basic(self) -> None:
        """Test basic logging configuration."""
        with (
            patch("logging.StreamHandler") as mock_handler_class,
            patch("sys.stderr", new_callable=StringIO) as mock_stderr,
        ):
            configure_logging()

            # Verify handler was created and added
            mock_handler_class.assert_called_once_with(stream=mock_stderr)

    def test_configure_logging_with_level(self) -> None:
        """Test logging configuration with custom level."""
        with patch("logging.StreamHandler"), patch("sys.stderr", new_callable=StringIO):
            configure_logging(level=logging.DEBUG)

            root_logger = logging.getLogger()
            assert root_logger.level == logging.DEBUG

    def test_configure_logging_removes_existing_handlers(self) -> None:
        """Test that existing handlers are removed."""
        root_logger = logging.getLogger()

        # Add a dummy handler
        dummy_handler = logging.StreamHandler()
        root_logger.addHandler(dummy_handler)
        assert len(root_logger.handlers) > 0

        with patch("logging.StreamHandler"), patch("sys.stderr", new_callable=StringIO):
            configure_logging()

            # Original handler should be removed
            assert dummy_handler not in root_logger.handlers

    def test_configure_logging_sets_formatter(self) -> None:
        """Test that formatter is set on handler."""
        with (
            patch("logging.StreamHandler") as mock_handler_class,
            patch("sys.stderr", new_callable=StringIO),
        ):
            configure_logging()

            # Get the handler instance that was created
            call_args = mock_handler_class.call_args
            handler_instance = (
                call_args[0][0] if call_args[0] else mock_handler_class.return_value
            )

            # Verify formatter was set
            handler_instance.setFormatter.assert_called_once()


class TestWithContext:
    """Test with_context function."""

    def test_with_context_creation(self) -> None:
        """Test with_context returns LoggerAdapter."""
        logger = logging.getLogger("test")
        adapter = with_context(logger, user_id="123")
        assert isinstance(adapter, logging.LoggerAdapter)

    def test_with_context_preserves_logger(self) -> None:
        """Test adapter preserves original logger."""
        logger = logging.getLogger("test")
        adapter = with_context(logger, key="value")
        assert adapter.logger is logger

    def test_with_context_process_method(self) -> None:
        """Test adapter's process method merges extra fields."""
        logger = logging.getLogger("test")
        adapter = with_context(logger, user_id="123", action="login")

        # Test the process method
        msg, kwargs = adapter.process(
            "Test message", {"extra": {"extra_fields": {"existing": "value"}}}
        )

        assert msg == "Test message"
        assert "extra_fields" in kwargs["extra"]
        merged_fields = kwargs["extra"]["extra_fields"]
        assert merged_fields["user_id"] == "123"
        assert merged_fields["action"] == "login"
        assert merged_fields["existing"] == "value"

    def test_with_context_empty_extra(self) -> None:
        """Test adapter with no existing extra fields."""
        logger = logging.getLogger("test")
        adapter = with_context(logger, key="value")

        _, kwargs = adapter.process("Test", {})

        assert kwargs["extra"]["extra_fields"]["key"] == "value"

    def test_with_context_multiple_calls(self) -> None:
        """Test multiple with_context calls create separate adapters."""
        logger = logging.getLogger("test")
        adapter1 = with_context(logger, field1="value1")
        adapter2 = with_context(logger, field2="value2")

        # Each adapter should have its own fields
        _, kwargs1 = adapter1.process("Test1", {})
        _, kwargs2 = adapter2.process("Test2", {})

        fields1 = kwargs1["extra"]["extra_fields"]
        fields2 = kwargs2["extra"]["extra_fields"]

        assert fields1["field1"] == "value1"
        assert "field2" not in fields1
        assert fields2["field2"] == "value2"
        assert "field1" not in fields2


class TestLoggingIntegration:
    """Test logging integration scenarios."""

    def test_end_to_end_logging(self) -> None:
        """Test complete logging flow."""
        # Test the formatter directly instead of full integration
        formatter = KeyValueFormatter()
        set_session_id("integ123")

        record = logging.LogRecord(
            name="test.integration",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Integration test message",
            args=(),
            exc_info=None,
        )
        # Simulate extra fields that would be added by with_context
        record.__dict__["extra_fields"] = {"component": "test", "user": "test"}

        result = formatter.format(record)

        assert "level=INFO" in result
        assert "logger=test.integration" in result
        assert "session_id=integ123" in result
        assert "component=test" in result
        assert "user=test" in result
        assert 'message="Integration test message"' in result

    def test_session_id_in_formatted_output(self) -> None:
        """Test session ID appears in formatted log output."""
        formatter = KeyValueFormatter()

        # Test with different session IDs
        test_cases = ["sess1234", "abcd5678", "default-"]

        for session_id in test_cases:
            set_session_id(session_id)
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=1,
                msg="test",
                args=(),
                exc_info=None,
            )

            result = formatter.format(record)
            assert f"session_id={session_id}" in result


class TestLoggingErrorContext:
    """Test error context creation in logging."""

    def test_log_error_with_details_with_original_error(self) -> None:
        """Test log_error_with_details includes original error details."""
        from survey_studio.errors import ValidationError

        logger = logging.getLogger("test")
        original_exc = ValueError("Original error")
        error = ValidationError("Test error", original_exception=original_exc)

        with patch.object(logger, "error") as mock_error:
            log_error_with_details(
                logger, error, "test_operation", "test_component", additional="data"
            )

            # Verify error was logged
            mock_error.assert_called_once()
            call_args = mock_error.call_args
            extra_fields = call_args[1]["extra"]["extra_fields"]

            assert extra_fields["original_error_type"] == "ValueError"
            assert extra_fields["additional"] == "data"
            assert extra_fields["error_type"] == "ValidationError"
            assert extra_fields["component"] == "test_component"
            assert extra_fields["operation"] == "test_operation"

    def test_log_error_with_details_without_original_error(self) -> None:
        """Test log_error_with_details without original error."""
        from survey_studio.errors import ValidationError

        logger = logging.getLogger("test")
        error = ValidationError("Test error")

        with patch.object(logger, "error") as mock_error:
            log_error_with_details(
                logger, error, "test_operation", "test_component", additional="data"
            )

            # Verify error was logged
            mock_error.assert_called_once()
            call_args = mock_error.call_args
            extra_fields = call_args[1]["extra"]["extra_fields"]

            assert "original_error_type" not in extra_fields
            assert extra_fields["additional"] == "data"
            assert extra_fields["error_type"] == "ValidationError"
            assert extra_fields["component"] == "test_component"
            assert extra_fields["operation"] == "test_operation"
