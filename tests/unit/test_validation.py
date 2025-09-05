"""Unit tests for validation.py module."""

from __future__ import annotations

import pytest

from survey_studio.errors import ValidationError
from survey_studio.validation import (
    ALLOWED_MODELS,
    MAX_NUM_PAPERS,
    MAX_TOPIC_LENGTH,
    clamp,
    sanitize_text,
    validate_model,
    validate_num_papers,
    validate_openai_key,
    validate_topic,
)

# Constants for magic numbers
TEST_VALUE_5 = 5
TEST_VALUE_10 = 10
TEST_VALUE_50 = 50
TEST_VALUE_100 = 100
TEST_VALUE_200 = 200
TEST_VALUE_25 = 25
EXPECTED_MODEL_COUNT = 3


class TestValidateTopic:
    """Test validate_topic function with various inputs."""

    def test_valid_topic(self, valid_topic: str) -> None:
        """Test valid topic returns cleaned topic."""
        result = validate_topic(valid_topic)
        assert result == valid_topic

    def test_topic_with_whitespace(self) -> None:
        """Test topic with leading/trailing whitespace."""
        topic = "  Test Topic  "
        result = validate_topic(topic)
        assert result == "Test Topic"

    def test_empty_topic_raises_error(self, invalid_topic_empty: str) -> None:
        """Test empty topic raises ValidationError."""
        with pytest.raises(ValidationError, match="topic must be a non-empty string"):
            validate_topic(invalid_topic_empty)

    def test_whitespace_only_topic_raises_error(
        self, invalid_topic_whitespace: str
    ) -> None:
        """Test whitespace-only topic raises ValidationError."""
        with pytest.raises(ValidationError, match="topic must be a non-empty string"):
            validate_topic(invalid_topic_whitespace)

    def test_topic_too_long_raises_error(self, invalid_topic_too_long: str) -> None:
        """Test topic exceeding max length raises ValidationError."""
        with pytest.raises(ValidationError, match="topic is too long"):
            validate_topic(invalid_topic_too_long)

    def test_topic_at_max_length(self) -> None:
        """Test topic at maximum allowed length."""
        topic = "A" * MAX_TOPIC_LENGTH
        result = validate_topic(topic)
        assert result == topic

    def test_topic_sanitization(self) -> None:
        """Test topic sanitization removes control characters."""
        topic = "Test\x00Topic\x01With\x02Control"
        result = validate_topic(topic)
        assert result == "TestTopicWithControl"


class TestValidateNumPapers:
    """Test validate_num_papers function with various inputs."""

    def test_valid_num_papers(self, valid_num_papers: int) -> None:
        """Test valid number of papers."""
        result = validate_num_papers(valid_num_papers)
        assert result == valid_num_papers

    def test_zero_papers_raises_error(self, invalid_num_papers_zero: int) -> None:
        """Test zero papers raises ValidationError."""
        with pytest.raises(
            ValidationError, match="num_papers must be a positive integer"
        ):
            validate_num_papers(invalid_num_papers_zero)

    def test_negative_papers_raises_error(
        self, invalid_num_papers_negative: int
    ) -> None:
        """Test negative papers raises ValidationError."""
        with pytest.raises(
            ValidationError, match="num_papers must be a positive integer"
        ):
            validate_num_papers(invalid_num_papers_negative)

    def test_too_many_papers_raises_error(
        self, invalid_num_papers_too_large: int
    ) -> None:
        """Test too many papers raises ValidationError."""
        with pytest.raises(ValidationError, match="num_papers too large"):
            validate_num_papers(invalid_num_papers_too_large)

    def test_max_papers_allowed(self) -> None:
        """Test maximum allowed papers."""
        result = validate_num_papers(MAX_NUM_PAPERS)
        assert result == MAX_NUM_PAPERS

    def test_min_papers_allowed(self) -> None:
        """Test minimum allowed papers."""
        result = validate_num_papers(1)
        assert result == 1

    def test_non_integer_type_raises_error(self) -> None:
        """Test non-integer type raises TypeError."""
        with pytest.raises(TypeError):
            validate_num_papers("5")  # type: ignore[arg-type]


class TestValidateModel:
    """Test validate_model function with various inputs."""

    def test_valid_model(self, valid_model: str) -> None:
        """Test valid model name."""
        result = validate_model(valid_model)
        assert result == valid_model

    def test_all_allowed_models(self) -> None:
        """Test all allowed models."""
        for model in ALLOWED_MODELS:
            result = validate_model(model)
            assert result == model

    def test_invalid_model_raises_error(self, invalid_model: str) -> None:
        """Test invalid model raises ValidationError."""
        with pytest.raises(ValidationError, match="model must be one of"):
            validate_model(invalid_model)

    def test_case_sensitive_model(self) -> None:
        """Test model validation is case sensitive."""
        with pytest.raises(ValidationError):
            validate_model("GPT-4O-MINI")  # Wrong case


class TestValidateOpenaiKey:
    """Test validate_openai_key function with various scenarios."""

    def test_valid_key_from_env(self, mock_env_vars: None) -> None:  # noqa: ARG002
        """Test valid key from environment."""
        result = validate_openai_key()
        assert result == "test-api-key-12345"

    def test_missing_key_raises_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test missing key raises ValidationError."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(ValidationError, match="Missing API key"):
            validate_openai_key()

    def test_empty_key_raises_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test empty key raises ValidationError."""
        monkeypatch.setenv("OPENAI_API_KEY", "")
        with pytest.raises(ValidationError, match="Missing API key"):
            validate_openai_key()

    def test_whitespace_only_key_raises_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test whitespace-only key raises ValidationError."""
        monkeypatch.setenv("OPENAI_API_KEY", "   \t\n  ")
        with pytest.raises(ValidationError, match="Missing API key"):
            validate_openai_key()

    def test_custom_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test custom environment variable name."""
        monkeypatch.setenv("CUSTOM_API_KEY", "custom-key-123")
        result = validate_openai_key("CUSTOM_API_KEY")
        assert result == "custom-key-123"

    def test_custom_env_var_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: ARG002
        """Test custom environment variable missing."""
        with pytest.raises(
            ValidationError, match="Missing API key: set CUSTOM_API_KEY"
        ):
            validate_openai_key("CUSTOM_API_KEY")


class TestSanitizeText:
    """Test sanitize_text function with various inputs."""

    def test_normal_text_unchanged(self) -> None:
        """Test normal text is unchanged."""
        text = "Normal text with spaces"
        result = sanitize_text(text)
        assert result == text

    def test_whitespace_collapsed(self, test_text_with_whitespace: str) -> None:
        """Test whitespace is properly collapsed."""
        result = sanitize_text(test_text_with_whitespace)
        assert result == "Test text with multiple spaces"

    def test_control_characters_removed(
        self, test_text_with_control_chars: str
    ) -> None:
        """Test control characters are removed."""
        result = sanitize_text(test_text_with_control_chars)
        assert result == "Testtextwithcontrolchars"

    def test_unicode_preserved(self, test_text_unicode: str) -> None:
        """Test unicode characters are preserved."""
        result = sanitize_text(test_text_unicode)
        assert result == test_text_unicode

    def test_empty_string(self) -> None:
        """Test empty string handling."""
        result = sanitize_text("")
        assert result == ""

    def test_only_whitespace(self) -> None:
        """Test string with only whitespace."""
        result = sanitize_text("   \t\n  ")
        assert result == ""

    def test_mixed_whitespace_and_control(self) -> None:
        """Test mixed whitespace and control characters."""
        text = "  Test\x00 \t\n  Text  "
        result = sanitize_text(text)
        assert result == "Test Text"


class TestClamp:
    """Test clamp function with various inputs."""

    def test_value_within_bounds(self) -> None:
        """Test value within bounds returns unchanged."""
        result = clamp(TEST_VALUE_5, 0, TEST_VALUE_10)
        assert result == TEST_VALUE_5

    def test_value_below_min(self) -> None:
        """Test value below min returns min."""
        result = clamp(-5, 0, 10)
        assert result == 0

    def test_value_above_max(self) -> None:
        """Test value above max returns max."""
        result = clamp(15, 0, TEST_VALUE_10)
        assert result == TEST_VALUE_10

    def test_value_at_min(self) -> None:
        """Test value at min boundary."""
        result = clamp(0, 0, 10)
        assert result == 0

    def test_value_at_max(self) -> None:
        """Test value at max boundary."""
        result = clamp(TEST_VALUE_10, 0, TEST_VALUE_10)
        assert result == TEST_VALUE_10

    def test_equal_min_max(self) -> None:
        """Test when min equals max."""
        result = clamp(TEST_VALUE_5, TEST_VALUE_5, TEST_VALUE_5)
        assert result == TEST_VALUE_5

    def test_negative_bounds(self) -> None:
        """Test with negative bounds."""
        result = clamp(-5, -10, -1)
        assert result == -5  # noqa: PLR2004

    def test_large_integer_values(self) -> None:
        """Test with large integer values."""
        result = clamp(TEST_VALUE_100, 0, TEST_VALUE_50)
        assert result == TEST_VALUE_50


class TestConstants:
    """Test module constants."""

    def test_allowed_models_tuple(self) -> None:
        """Test ALLOWED_MODELS is a tuple with expected values."""
        assert isinstance(ALLOWED_MODELS, tuple)
        assert len(ALLOWED_MODELS) == EXPECTED_MODEL_COUNT
        assert "gpt-4o-mini" in ALLOWED_MODELS
        assert "gpt-4o" in ALLOWED_MODELS
        assert "gpt-3.5-turbo" in ALLOWED_MODELS

    def test_max_topic_length(self) -> None:
        """Test MAX_TOPIC_LENGTH constant."""
        assert isinstance(MAX_TOPIC_LENGTH, int)
        assert MAX_TOPIC_LENGTH == TEST_VALUE_200

    def test_max_num_papers(self) -> None:
        """Test MAX_NUM_PAPERS constant."""
        assert isinstance(MAX_NUM_PAPERS, int)
        assert MAX_NUM_PAPERS == TEST_VALUE_25
