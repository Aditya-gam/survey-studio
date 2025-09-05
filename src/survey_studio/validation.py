"""Input validation and sanitization utilities."""

from __future__ import annotations

import os

from .errors import ValidationError

ALLOWED_MODELS: tuple[str, ...] = ("gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo")


def validate_topic(topic: str) -> str:
    topic = topic.strip()
    if not topic:
        raise ValidationError("topic must be a non-empty string")
    if len(topic) > 200:
        raise ValidationError("topic is too long; please shorten to <= 200 chars")
    return sanitize_text(topic)


def validate_num_papers(num_papers: int) -> int:
    if num_papers <= 0:
        raise ValidationError("num_papers must be a positive integer")
    if num_papers > 25:
        raise ValidationError("num_papers too large; please choose <= 25")
    return num_papers


def validate_model(model: str) -> str:
    if model not in ALLOWED_MODELS:
        raise ValidationError(f"model must be one of: {', '.join(ALLOWED_MODELS)}")
    return model


def validate_openai_key(env_var: str = "OPENAI_API_KEY") -> str:
    key = os.getenv(env_var, "").strip()
    if not key:
        raise ValidationError(f"Missing API key: set {env_var}")
    return key


def sanitize_text(text: str) -> str:
    """Basic sanitization for user-provided text fields."""

    # Collapse whitespace and remove dangerous control characters
    collapsed = " ".join(text.split())
    safe = "".join(ch for ch in collapsed if ch.isprintable())
    return safe


def clamp(value: int, min_value: int, max_value: int) -> int:
    return max(min_value, min(max_value, value))
