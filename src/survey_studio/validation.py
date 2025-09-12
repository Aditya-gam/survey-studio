"""Input validation and sanitization utilities."""

from __future__ import annotations

import datetime
import os
import re

from survey_studio.core.errors import ValidationError

ALLOWED_MODELS: tuple[str, ...] = ("gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo")
MAX_TOPIC_LENGTH: int = 200
MIN_TOPIC_LENGTH: int = 3
MAX_NUM_PAPERS: int = 10
MAX_KEYWORDS: int = 10
MIN_YEAR: int = 1900


def validate_topic(topic: str) -> str:
    topic = topic.strip()
    if not topic:
        raise ValidationError("topic must be a non-empty string")
    if len(topic) < MIN_TOPIC_LENGTH:
        raise ValidationError(f"topic must be at least {MIN_TOPIC_LENGTH} characters long")
    if len(topic) > MAX_TOPIC_LENGTH:
        raise ValidationError("topic is too long; please shorten to <= 200 chars")
    if not validate_topic_characters(topic):
        raise ValidationError(
            "topic contains invalid characters; use only alphanumeric, spaces, "
            + "and common punctuation (.,!?-:;()[]\"')"
        )
    return sanitize_text(topic)


def validate_num_papers(num_papers: int) -> int:
    if num_papers <= 0:
        raise ValidationError("num_papers must be a positive integer")
    if num_papers > MAX_NUM_PAPERS:
        raise ValidationError(f"num_papers too large; please choose <= {MAX_NUM_PAPERS}")
    return num_papers


def validate_model(model: str) -> str:
    if model not in ALLOWED_MODELS:
        raise ValidationError(f"model must be one of: {', '.join(ALLOWED_MODELS)}")
    return model


def validate_openai_key(env_var: str = "OPENAI_API_KEY") -> str:
    key = os.getenv(env_var, "").strip()
    if not key:
        raise ValidationError(f"Missing API key: set {env_var}")
    if not validate_api_key_format(key):
        raise ValidationError(f"Invalid API key format for {env_var}")
    return key


def sanitize_text(text: str) -> str:
    """Enhanced sanitization for user-provided text fields with security."""

    # Collapse whitespace and remove dangerous control characters
    collapsed = " ".join(text.split())

    # Remove potentially dangerous characters while preserving readability
    sanitized: list[str] = []
    control_charachter_ord = 32  # noqa: N806
    dangerous_chars: list[str] = [  # noqa: N806
        "<",
        ">",
        "&",
        '"',
        "'",
        "\\",
        "`",
        "$",
        "|",
        ";",
        "{",
        "}",
    ]

    for ch in collapsed:
        # Allow printable characters but filter out dangerous ones
        if ch.isprintable() and ord(ch) >= control_charachter_ord and ch not in dangerous_chars:
            sanitized.append(ch)

    return "".join(sanitized)


def clamp(value: int, min_value: int, max_value: int) -> int:
    return max(min_value, min(max_value, value))


def validate_topic_characters(topic: str) -> bool:
    """Validate that topic contains only sane characters."""
    # Allow alphanumeric, spaces, common punctuation, and unicode letters
    # Reject characters that could cause injection issues
    pattern = r'^[\w\s.,!?\-:\;\(\)\[\]\'"]+$'
    return bool(re.match(pattern, topic, re.UNICODE))


def validate_keywords(keywords_str: str) -> list[str]:
    """Validate and parse comma-separated keywords."""
    if not keywords_str.strip():
        return []

    # Split by comma and clean up
    keywords = [kw.strip() for kw in keywords_str.split(",") if kw.strip()]

    # Remove empty entries
    keywords = [kw for kw in keywords if kw]

    if len(keywords) > MAX_KEYWORDS:
        raise ValidationError(f"Too many keywords; maximum is {MAX_KEYWORDS}")

    # Validate each keyword format (allow spaces for multi-word keywords)
    for keyword in keywords:
        # Check for invalid characters explicitly
        if any(char in keyword for char in "@#&!") or not re.match(r"^[a-zA-Z0-9\s_-]+$", keyword):
            raise ValidationError(
                f"Invalid keyword '{keyword}'; use only alphanumeric characters, "
                + "spaces, hyphens, and underscores"
            )

    return keywords


def validate_year_range(start_year: int, end_year: int) -> tuple[int, int]:
    """Validate year range for literature search."""
    current_year = datetime.datetime.now().year

    if start_year < MIN_YEAR:
        raise ValidationError(f"Start year must be >= {MIN_YEAR}")

    if end_year > current_year + 1:  # Allow current year + 1 for upcoming publications
        raise ValidationError(f"End year cannot be > {current_year + 1}")

    if start_year > end_year:
        raise ValidationError("Start year cannot be greater than end year")

    return start_year, end_year


def validate_api_key_format(api_key: str) -> bool:
    """Validate OpenAI API key format."""
    # OpenAI keys start with 'sk-' and have specific length patterns
    if not api_key.startswith("sk-"):
        return False

    # Remove prefix and check remaining format
    key_body = api_key[3:]

    # Should be alphanumeric with possible underscores/hyphens
    return bool(re.match(r"^[a-zA-Z0-9_-]{20,}$", key_body))
