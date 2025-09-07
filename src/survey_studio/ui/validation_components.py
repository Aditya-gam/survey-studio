"""UI validation components for Survey Studio.

Provides reusable Streamlit components for validation feedback, helper text,
and advanced options with dynamic validation.
"""

from __future__ import annotations

import datetime
from typing import Any

import streamlit as st

from survey_studio.validation import (
    MAX_KEYWORDS,
    MAX_NUM_PAPERS,
    MAX_TOPIC_LENGTH,
    MIN_TOPIC_LENGTH,
    MIN_YEAR,
    validate_api_key_format,
    validate_keywords,
    validate_topic_characters,
    validate_year_range,
)


def render_validation_helper(text: str, validation_state: str) -> None:
    """Render contextual helper text with color coding.

    Args:
        text: The helper text to display
        validation_state: "valid", "invalid", or "warning"
    """
    if validation_state == "valid":
        st.success(text, icon="✅")
    elif validation_state == "invalid":
        st.error(text, icon="❌")
    elif validation_state == "warning":
        st.warning(text, icon="⚠️")
    else:
        st.info(text, icon="ℹ️")


def validate_topic_input(topic: str) -> tuple[str, str]:
    """Validate topic input and return helper text with state.

    Returns:
        Tuple of (helper_text, validation_state)
    """
    if not topic.strip():
        return "Please enter a research topic", "warning"

    if len(topic.strip()) < MIN_TOPIC_LENGTH:
        return f"Topic must be at least {MIN_TOPIC_LENGTH} characters long", "invalid"

    if len(topic.strip()) > MAX_TOPIC_LENGTH:
        return f"Topic is too long (max {MAX_TOPIC_LENGTH} characters)", "invalid"

    if not validate_topic_characters(topic):
        return "Use only alphanumeric, spaces, and common punctuation", "invalid"

    return f"Valid topic ({len(topic)} characters)", "valid"


def validate_papers_input(num_papers: int) -> tuple[str, str]:
    """Validate number of papers input and return helper text with state.

    Returns:
        Tuple of (helper_text, validation_state)
    """
    if num_papers < 1:
        return "Number of papers must be at least 1", "invalid"

    if num_papers > MAX_NUM_PAPERS:
        return f"Maximum {MAX_NUM_PAPERS} papers allowed", "invalid"

    return f"Will search for {num_papers} papers", "valid"


def validate_keywords_input(keywords_str: str) -> tuple[str, str]:
    """Validate keywords input and return helper text with state.

    Returns:
        Tuple of (helper_text, validation_state)
    """
    if not keywords_str.strip():
        return "Optional: add comma-separated keywords to refine search", "info"

    try:
        keywords = validate_keywords(keywords_str)
        if len(keywords) > MAX_KEYWORDS:
            return f"Too many keywords (max {MAX_KEYWORDS})", "invalid"
        return f"Valid keywords: {', '.join(keywords)}", "valid"
    except Exception as e:
        return str(e), "invalid"


def validate_year_range_input(start_year: int, end_year: int) -> tuple[str, str]:
    """Validate year range input and return helper text with state.

    Returns:
        Tuple of (helper_text, validation_state)
    """
    try:
        validate_year_range(start_year, end_year)
        current_year = datetime.datetime.now().year
        if start_year == MIN_YEAR and end_year == current_year + 1:
            return "Searching all available years", "info"
        return f"Searching papers from {start_year} to {end_year}", "valid"
    except Exception as e:
        return str(e), "invalid"


def validate_api_key_available() -> tuple[str, str]:
    """Check if API key is available and return status.

    Returns:
        Tuple of (status_text, validation_state)
    """
    import os

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return "OpenAI API key not configured", "invalid"

    if not validate_api_key_format(api_key):
        return "Invalid API key format", "invalid"

    return "API key configured", "valid"


def render_advanced_options_sidebar() -> dict[str, Any]:
    """Render the collapsible advanced options section.

    Returns:
        Dictionary with validated advanced options
    """
    with st.sidebar.expander("🔧 Advanced Options", expanded=False):
        # Keywords input
        keywords_str = st.text_input(
            "Keywords (optional)",
            placeholder="machine learning, neural networks, transformers",
            help="Comma-separated keywords to refine the search",
            key="keywords_input",
        )

        # Year range inputs
        current_year = datetime.datetime.now().year
        col1, col2 = st.columns(2)

        with col1:
            start_year = st.number_input(
                "Start Year",
                min_value=MIN_YEAR,
                max_value=current_year + 1,
                value=MIN_YEAR,
                help="Earliest publication year to include",
                key="start_year_input",
            )

        with col2:
            end_year = st.number_input(
                "End Year",
                min_value=MIN_YEAR,
                max_value=current_year + 1,
                value=current_year + 1,
                help="Latest publication year to include",
                key="end_year_input",
            )

        # Validation feedback for advanced options
        if keywords_str:
            helper_text, state = validate_keywords_input(keywords_str)
            render_validation_helper(helper_text, state)

        if start_year != MIN_YEAR or end_year != current_year + 1:
            helper_text, state = validate_year_range_input(start_year, end_year)
            render_validation_helper(helper_text, state)

        # Validate and return processed values
        advanced_options: dict[str, Any] = {}

        if keywords_str.strip():
            try:
                advanced_options["keywords"] = validate_keywords(keywords_str)
            except Exception:
                advanced_options["keywords"] = []

        try:
            advanced_options["start_year"], advanced_options["end_year"] = (
                validate_year_range(start_year, end_year)
            )
        except Exception:
            # Use defaults if validation fails
            advanced_options["start_year"] = MIN_YEAR
            advanced_options["end_year"] = current_year + 1

        return advanced_options


def render_validation_status(
    topic: str, num_papers: int, advanced_options: dict[str, Any] | None = None
) -> bool:
    """Render comprehensive validation status and return overall validity.

    Args:
        topic: Research topic string
        num_papers: Number of papers
        advanced_options: Optional advanced options dictionary

    Returns:
        True if all validations pass, False otherwise
    """
    validations = [
        ("topic", validate_topic_input(topic)),
        ("papers", validate_papers_input(num_papers)),
        ("api_key", validate_api_key_available()),
    ]

    all_valid = True

    # Process basic validations
    for _name, (helper_text, state) in validations:
        if state == "invalid":
            all_valid = False
        render_validation_helper(helper_text, state)

    # Process advanced options if provided
    if advanced_options:
        all_valid &= _validate_advanced_options(advanced_options)

    return all_valid


def _validate_advanced_options(advanced_options: dict[str, Any]) -> bool:
    """Validate advanced options and return overall validity."""
    all_valid = True

    if "keywords" in advanced_options and advanced_options["keywords"]:
        keywords_str = ", ".join(advanced_options["keywords"])
        helper_text, state = validate_keywords_input(keywords_str)
        if state == "invalid":
            all_valid = False
        render_validation_helper(helper_text, state)

    if "start_year" in advanced_options and "end_year" in advanced_options:
        helper_text, state = validate_year_range_input(
            advanced_options["start_year"], advanced_options["end_year"]
        )
        if state == "invalid":
            all_valid = False
        render_validation_helper(helper_text, state)

    return all_valid
