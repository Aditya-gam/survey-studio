"""Structured logging utilities for Survey Studio.

Provides a simple key=value formatter and helpers for attaching a session_id
to every log record. This keeps logs machine-parsable and consistent.
Includes security features for sensitive data redaction.
"""

from __future__ import annotations

from contextvars import ContextVar
import logging
import re
import sys
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # TCH003: only import Mapping for typing
    from collections.abc import Mapping
import uuid

_session_id_var: ContextVar[str] = ContextVar("session_id", default="-")

# Regex patterns for sensitive data detection
SENSITIVE_PATTERNS = [
    (
        re.compile(
            r"(?i)(api[_-]?key|token|secret|password|passwd)\s*[:=]\s*"
            r'["\']?([^"\'\s]+)'
        ),
        r"\1=***REDACTED***",
    ),
    (re.compile(r"(?i)(bearer\s+)([a-zA-Z0-9_-]+)"), r"\1***REDACTED***"),
    (re.compile(r"(?i)(sk-[a-zA-Z0-9]{32,})"), r"***REDACTED***"),
    (
        re.compile(r'(?i)(\w*key\w*"?\s*:\s*")[^"]+(")', re.IGNORECASE),
        r"\1***REDACTED***\2",
    ),
]

MAX_LOG_VALUE_LENGTH = 1000


def new_session_id() -> str:
    """Return a new session id string.

    Uses UUID4, shortened to 8 chars for readability while remaining unique
    enough for session scoping in logs.
    """

    return uuid.uuid4().hex[:8]


def set_session_id(session_id: str) -> None:
    _session_id_var.set(session_id)


def get_session_id() -> str:
    return _session_id_var.get()


def redact_sensitive_data(data: dict[str, Any]) -> dict[str, Any]:
    """Redact sensitive data from logging data.

    Removes or redacts API keys, tokens, passwords, and other sensitive information.
    Also truncates long values to prevent log pollution.
    """
    redacted = {}

    for key, value in data.items():
        # Convert to string for processing
        str_value = str(value)

        # Apply redaction patterns
        for pattern, replacement in SENSITIVE_PATTERNS:
            str_value = pattern.sub(replacement, str_value)

        # Truncate long values
        if len(str_value) > MAX_LOG_VALUE_LENGTH:
            str_value = str_value[:MAX_LOG_VALUE_LENGTH] + "...[TRUNCATED]"

        # Check key names for sensitive data
        key_lower = key.lower()
        sensitive_keys = ["key", "token", "secret", "password", "passwd", "auth"]
        if any(sensitive in key_lower for sensitive in sensitive_keys):
            redacted[key] = "***REDACTED***"
        else:
            redacted[key] = str_value

    return redacted


class KeyValueFormatter(logging.Formatter):
    """Format records as key=value pairs on a single line with security redaction."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401 - docstring inherited
        import time

        base: dict[str, Any] = {
            "timestamp": time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(record.created)
            ),
            "level": record.levelname,
            "logger": record.name,
            "session_id": get_session_id(),
            "message": record.getMessage(),
        }

        # Merge any extra fields added via LoggerAdapter or `extra=...`
        extra_fields = record.__dict__.get("extra_fields")
        if isinstance(extra_fields, dict):
            base.update(extra_fields)

        # Redact sensitive data before formatting
        base = redact_sensitive_data(base)

        return " ".join(f"{k}={_safe(v)}" for k, v in base.items())


def _safe(value: Any) -> str:
    text = str(value)
    # Quote values with whitespace
    return f'"{text}"' if any(c.isspace() for c in text) else text


def configure_logging(level: int = logging.INFO) -> None:
    """Configure root logging with our key=value formatter."""

    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(KeyValueFormatter())

    root = logging.getLogger()
    root.setLevel(level)
    # Remove existing handlers to avoid duplicate logs when re-configuring
    for h in root.handlers:
        root.removeHandler(h)
    root.addHandler(handler)


def with_context(
    logger: logging.Logger, **fields: Any
) -> logging.LoggerAdapter[logging.Logger]:
    """Return a LoggerAdapter that injects extra key=value fields."""

    class _Adapter(logging.LoggerAdapter[logging.Logger]):
        def process(
            self, msg: str, kwargs: Mapping[str, Any]
        ) -> tuple[str, dict[str, Any]]:
            extra: dict[str, Any] = dict(kwargs.get("extra", {}))
            current: dict[str, Any] = dict(extra.get("extra_fields", {}))
            merged: dict[str, Any] = {**current, **fields}

            # Ensure session_id is always present
            if "session_id" not in merged:
                merged["session_id"] = get_session_id()

            new_kwargs: dict[str, Any] = dict(kwargs)
            new_kwargs["extra"] = {"extra_fields": merged}
            return msg, new_kwargs

    return _Adapter(logger, {})


def log_error_with_details(
    logger: logging.Logger,
    error: Exception,
    operation: str,
    component: str,
    **additional_context: Any,
) -> None:
    """Log an error with structured details and security redaction."""
    from .errors import get_error_details

    error_details = get_error_details(error)

    context = {
        "component": component,
        "operation": operation,
        "error_id": error_details.get("error_id", "unknown"),
        "error_type": error_details["type"],
        "severity": error_details.get("severity", "error"),
        **additional_context,
    }

    # Add original exception details if available
    if "original_error" in error_details:
        context["original_error_type"] = error_details["original_error"]["type"]

    # Redact sensitive data from context
    redacted_context = redact_sensitive_data(context)

    logger.error(
        error_details["message"],
        extra={"extra_fields": redacted_context},
    )
