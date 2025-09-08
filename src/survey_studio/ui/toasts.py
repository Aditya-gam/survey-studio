"""Toast notification system for user-friendly error and status messages.

Provides components for displaying success, error, warning, and info notifications
using Streamlit's native toast system with enhanced functionality for error tracking.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import streamlit as st

from survey_studio.errors import (
    SurveyStudioError,
    get_error_details,
    get_user_friendly_message,
)
from survey_studio.logging import get_session_id

# Session state key for error history
ERROR_HISTORY_KEY = "toast_error_history"
MAX_ERROR_HISTORY = 10


def _get_error_history() -> list[dict[str, Any]]:
    """Get the current error history from session state."""
    if ERROR_HISTORY_KEY not in st.session_state:
        st.session_state[ERROR_HISTORY_KEY] = []

    history = st.session_state[ERROR_HISTORY_KEY]
    # Ensure we return the correct type
    if not isinstance(history, list):
        st.session_state[ERROR_HISTORY_KEY] = []
        return []

    # Type assertion to help Pyright understand the type
    return history  # type: ignore[return-value]


def _add_to_error_history(error_data: dict[str, Any]) -> None:
    """Add an error to the history, keeping only the last 10 errors."""
    history = _get_error_history()
    history.append(error_data)

    # Keep only the last N errors
    if len(history) > MAX_ERROR_HISTORY:
        history.pop(0)

    st.session_state[ERROR_HISTORY_KEY] = history


def show_success_toast(message: str, details: str | None = None) -> None:
    """Display a success toast notification.

    Args:
        message: The success message to display
        details: Optional additional details to show in an expander
    """
    # Use Streamlit's built-in toast for success
    st.toast(f"✅ {message}", icon="✅")

    # Only show details in expander if provided, no persistent success message
    if details:
        with st.expander("📋 Success Details", expanded=False):
            st.write(details)


def show_error_toast(
    message: str,
    error_id: str,
    details: str | None = None,
    exception: Exception | None = None,
) -> None:
    """Display an error toast notification with tracking.

    Args:
        message: The error message to display to users
        error_id: Unique error identifier for tracking
        details: Optional technical details to show in an expander
        exception: Optional exception object for additional context
    """
    # Show the toast notification with more informative message
    st.toast(f"❌ {message}", icon="❌")

    # Add to error history
    error_data = {
        "timestamp": datetime.now().isoformat(),
        "message": message,
        "error_id": error_id,
        "details": details,
        "session_id": get_session_id(),
    }

    if exception:
        error_details = get_error_details(exception)
        error_data.update(
            {
                "exception_type": error_details["type"],
                "severity": error_details.get("severity", "error"),
                "context": error_details.get("context", {}),
            }
        )

    _add_to_error_history(error_data)

    # Only show toast, no persistent error messages on main page
    # All error details and tips are in the expander below

    # Show technical details and helpful tips in an expander
    with st.expander("🔧 Error Details & Help", expanded=False):
        # Show helpful context and next steps
        if "validation" in message.lower() or "invalid" in message.lower():
            st.info(
                "💡 **Tip**: Check the sidebar for specific validation issues and fix them "
                + "before trying again."
            )
        elif "api" in message.lower() or "key" in message.lower():
            st.info(
                "💡 **Tip**: Make sure you have configured at least one AI provider API key in "
                + "your environment variables or .env file."
            )
        elif "network" in message.lower() or "connection" in message.lower():
            st.info(
                "💡 **Tip**: Check your internet connection and try again. The service may be "
                + "temporarily unavailable."
            )
        elif "rate limit" in message.lower():
            st.info(
                "💡 **Tip**: You've hit a rate limit. Please wait a moment before trying again, or "
                + "consider using a different AI provider."
            )

        if details:
            st.markdown("**Technical Details:**")
            st.code(details, language="text")

        if exception and isinstance(exception, SurveyStudioError):
            st.markdown("**Error Information:**")
            st.json(
                {
                    "error_type": exception.__class__.__name__,
                    "severity": exception.severity.value,
                    "context": exception.context,
                    "original_exception": (
                        exception.original_exception.__class__.__name__
                        if exception.original_exception
                        else None
                    ),
                }
            )


def show_warning_toast(message: str, details: str | None = None) -> None:
    """Display a warning toast notification.

    Args:
        message: The warning message to display
        details: Optional additional details to show in an expander
    """
    # Use Streamlit's built-in toast for warnings
    st.toast(f"⚠️ {message}", icon="⚠️")

    # Show details if provided
    if details:
        with st.expander("📋 Warning Details", expanded=False):
            st.write(details)


def show_info_toast(message: str, details: str | None = None) -> None:
    """Display an info toast notification.

    Args:
        message: The info message to display
        details: Optional additional details to show in an expander
    """
    # Use Streamlit's built-in toast for info
    st.toast(f"ℹ️ {message}", icon="ℹ️")

    # Show details if provided
    if details:
        with st.expander("📋 Additional Information", expanded=False):
            st.write(details)


def show_error_panel(errors: list[dict[str, Any]] | None = None) -> None:
    """Display a persistent error panel with error history.

    Args:
        errors: Optional list of errors to display. If None, uses session error history.
    """
    if errors is None:
        errors = _get_error_history()

    if not errors:
        return

    st.subheader("🚨 Error History")
    st.caption(f"Showing {len(errors)} recent error(s)")

    # Create tabs for different error severities if we have severity info
    severities: set[str] = set()
    for error in errors:
        if "severity" in error and isinstance(error["severity"], str):
            severities.add(error["severity"])

    if len(severities) > 1:
        severity_list = list(severities)
        tabs = st.tabs(severity_list + ["All"])

        for i, severity in enumerate(severity_list):
            with tabs[i]:
                _render_error_list([e for e in errors if e.get("severity") == severity])

        with tabs[-1]:
            _render_error_list(errors)
    else:
        _render_error_list(errors)

    # Clear history button
    _, col2, _ = st.columns([1, 1, 1])
    with col2:
        if st.button("Clear Error History", type="secondary"):
            st.session_state[ERROR_HISTORY_KEY] = []
            st.rerun()


def _render_error_list(errors: list[dict[str, Any]]) -> None:
    """Render a list of errors in the error panel."""
    for i, error in enumerate(reversed(errors)):  # Most recent first
        with st.expander(
            f"{error['message']} (ID: {error['error_id'][:6]}...)",
            expanded=(i == 0),  # Expand the most recent error
        ):
            _render_single_error(error)


def _render_single_error(error: dict[str, Any]) -> None:
    """Render a single error in the error panel."""
    col1, col2 = st.columns([2, 1])

    with col1:
        st.write(f"**Message:** {error['message']}")
        st.write(f"**Time:** {error['timestamp']}")
        st.write(f"**Error ID:** `{error['error_id']}`")
        st.write(f"**Session:** `{error['session_id']}`")

        if "exception_type" in error:
            st.write(f"**Type:** {error['exception_type']}")

        if "severity" in error:
            severity_color = _get_severity_color(error["severity"])
            st.markdown(f"**Severity:** :{severity_color}[{error['severity'].upper()}]")

    with col2:
        if "context" in error and error["context"]:
            st.json(error["context"])

    if error.get("details"):
        st.code(error["details"], language="text")


def _get_severity_color(severity: str) -> str:
    """Get color for severity level."""
    severity_colors = {
        "info": "blue",
        "warning": "orange",
        "error": "red",
        "critical": "red",
    }
    return severity_colors.get(severity, "red")


def handle_exception_with_toast(
    exception: Exception, operation: str = "operation", show_details: bool = True
) -> None:
    """Handle an exception by showing appropriate toast notifications.

    Args:
        exception: The exception to handle
        operation: Description of the operation that failed
        show_details: Whether to show technical details
    """
    user_message = get_user_friendly_message(exception)

    if isinstance(exception, SurveyStudioError):
        _handle_survey_studio_error(exception, user_message, show_details)
    else:
        _handle_generic_error(exception, operation, user_message, show_details)


def _handle_survey_studio_error(
    exception: SurveyStudioError, user_message: str, show_details: bool
) -> None:
    """Handle Survey Studio specific errors with appropriate toast types."""
    error_id = exception.error_id
    severity = exception.severity.value
    details = str(exception) if show_details else None

    # Choose toast type based on severity
    if severity in ["critical", "error"]:
        show_error_toast(user_message, error_id, details=details, exception=exception)
    elif severity == "warning":
        show_warning_toast(user_message, details=details)
    else:  # info
        show_info_toast(user_message, details=details)


def _handle_generic_error(
    exception: Exception, operation: str, user_message: str, show_details: bool
) -> None:
    """Handle generic exceptions by generating error ID and showing error toast."""
    import uuid

    error_id = uuid.uuid4().hex[:8]
    details = f"{operation} failed: {str(exception)}" if show_details else None

    show_error_toast(user_message, error_id, details=details, exception=exception)


def show_retry_progress(attempt: int, max_attempts: int, service: str) -> None:
    """Show retry progress indicators.

    Args:
        attempt: Current retry attempt number
        max_attempts: Maximum number of retry attempts
        service: Name of the service being retried
    """
    progress = attempt / max_attempts

    # Show retry progress as toast and progress bar only
    st.toast(f"🔄 Retrying {service} service... (Attempt {attempt}/{max_attempts})", icon="🔄")
    st.progress(progress, text=f"Retry attempt {attempt} of {max_attempts}")

    if attempt == max_attempts:
        show_warning_toast(
            f"Maximum retry attempts reached for {service}",
            f"Attempted {max_attempts} times without success",
        )
