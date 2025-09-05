"""Structured logging utilities for Survey Studio.

Provides a simple key=value formatter and helpers for attaching a session_id
to every log record. This keeps logs machine-parsable and consistent.
"""

from __future__ import annotations

import logging
import sys
import uuid
from collections.abc import Mapping
from contextvars import ContextVar
from typing import Any

_session_id_var: ContextVar[str] = ContextVar("session_id", default="-")


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


class KeyValueFormatter(logging.Formatter):
    """Format records as key=value pairs on a single line."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401 - docstring inherited
        base: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "session_id": get_session_id(),
            "message": record.getMessage(),
        }

        # Merge any extra fields added via LoggerAdapter or `extra=...`
        extra_fields = record.__dict__.get("extra_fields")
        if isinstance(extra_fields, dict):
            base.update(extra_fields)

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
            new_kwargs: dict[str, Any] = dict(kwargs)
            new_kwargs["extra"] = {"extra_fields": merged}
            return msg, new_kwargs

    return _Adapter(logger, {})
