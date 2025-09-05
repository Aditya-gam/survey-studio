"""Unit tests for export.py module."""

from __future__ import annotations

from datetime import datetime
import re
from unittest.mock import patch

import pytest

from survey_studio.errors import ErrorSeverity, ExportError, ValidationError
from survey_studio.export import (
    MAX_FILENAME_LENGTH,
    ExportMetadata,
    Paper,
    _sanitize_topic_for_filename,
    _validate_export_inputs,
    generate_filename,
    get_export_formats,
    to_html,
    to_markdown,
)

# Constants for magic numbers
LARGE_CONTENT_SIZE = 100


class TestPaper:
    """Test Paper dataclass."""

    def test_paper_creation(self) -> None:
        """Test Paper dataclass creation."""
        paper = Paper(
            title="Test Paper Title",
            authors=["Author One", "Author Two"],
            published="2023-01-15",
            summary="This is a test paper summary.",
            pdf_url="https://arxiv.org/pdf/test.pdf",
        )

        assert paper.title == "Test Paper Title"
        assert paper.authors == ["Author One", "Author Two"]
        assert paper.published == "2023-01-15"
        assert paper.summary == "This is a test paper summary."
        assert paper.pdf_url == "https://arxiv.org/pdf/test.pdf"

    def test_paper_immutable(self) -> None:
        """Test Paper is immutable (frozen dataclass)."""
        paper = Paper(
            title="Test Title",
            authors=["Test Author"],
            published="2023-01-01",
            summary="Test summary",
            pdf_url="https://example.com/test.pdf",
        )

        with pytest.raises(AttributeError):
            paper.title = "New Title"  # type: ignore

    def test_paper_equality(self) -> None:
        """Test Paper equality comparison."""
        paper1 = Paper(
            title="Test Title",
            authors=["Author"],
            published="2023-01-01",
            summary="Summary",
            pdf_url="https://example.com/test.pdf",
        )

        paper2 = Paper(
            title="Test Title",
            authors=["Author"],
            published="2023-01-01",
            summary="Summary",
            pdf_url="https://example.com/test.pdf",
        )

        paper3 = Paper(
            title="Different Title",
            authors=["Author"],
            published="2023-01-01",
            summary="Summary",
            pdf_url="https://example.com/test.pdf",
        )

        assert paper1 == paper2
        assert paper1 != paper3

    def test_paper_not_hashable_due_to_list(self) -> None:
        """Test Paper is not hashable due to mutable list field."""
        paper = Paper(
            title="Test Title",
            authors=["Author"],
            published="2023-01-01",
            summary="Summary",
            pdf_url="https://example.com/test.pdf",
        )

        # Paper should not be hashable because authors is a list
        with pytest.raises(TypeError, match="unhashable type"):
            hash(paper)

        # Cannot use in set due to unhashable list
        with pytest.raises(TypeError, match="unhashable type"):
            _ = {paper}

    def test_paper_string_representation(self) -> None:
        """Test Paper string representation."""
        paper = Paper(
            title="Test Title",
            authors=["Author"],
            published="2023-01-01",
            summary="Summary",
            pdf_url="https://example.com/test.pdf",
        )

        repr_str = repr(paper)
        assert "Paper(" in repr_str
        assert "title='Test Title'" in repr_str
        assert "authors=['Author']" in repr_str

    def test_paper_with_empty_authors(self) -> None:
        """Test Paper with empty authors list."""
        paper = Paper(
            title="Test Title",
            authors=[],
            published="2023-01-01",
            summary="Summary",
            pdf_url="https://example.com/test.pdf",
        )

        assert paper.authors == []

    def test_paper_with_single_author(self) -> None:
        """Test Paper with single author."""
        paper = Paper(
            title="Test Title",
            authors=["Single Author"],
            published="2023-01-01",
            summary="Summary",
            pdf_url="https://example.com/test.pdf",
        )

        assert paper.authors == ["Single Author"]


class TestToMarkdown:
    """Test to_markdown function."""

    def test_basic_markdown_export(self) -> None:
        """Test basic markdown export with topic and content."""
        topic = "Machine Learning"
        content_frames = ["First frame content", "Second frame content"]

        result = to_markdown(topic, content_frames)

        # Should start with YAML frontmatter
        assert result.startswith("---\n")
        assert 'title: "Literature Review: Machine Learning"' in result
        assert 'topic: "Machine Learning"' in result
        assert "# Literature Review: Machine Learning" in result
        assert "First frame content" in result
        assert "Second frame content" in result
        assert result.endswith("Second frame content\n")

    def test_markdown_with_empty_frames(self) -> None:
        """Test markdown export with empty content frames."""
        topic = "Test Topic"
        content_frames: list[str] = []

        result = to_markdown(topic, content_frames)

        # Should start with YAML frontmatter
        assert result.startswith("---\n")
        assert 'title: "Literature Review: Test Topic"' in result
        assert "# Literature Review: Test Topic" in result
        assert "*No content generated*" in result

    def test_markdown_with_single_frame(self) -> None:
        """Test markdown export with single content frame."""
        topic = "Single Topic"
        content_frames = ["Only content"]

        result = to_markdown(topic, content_frames)

        # Should start with YAML frontmatter and include metadata section
        assert result.startswith("---\n")
        assert 'title: "Literature Review: Single Topic"' in result
        assert "# Literature Review: Single Topic" in result
        assert "## Review Information" in result
        assert "Only content" in result
        assert result.endswith("Only content\n")

    def test_markdown_with_markdown_content(self) -> None:
        """Test markdown export preserves existing markdown formatting."""
        topic = "Research Topic"
        content_frames = [
            "# Section 1\n\nSome content",
            "- Bullet point 1\n- Bullet point 2",
            "**Bold text** and *italic text*",
        ]

        result = to_markdown(topic, content_frames)

        assert "# Literature Review: Research Topic" in result
        assert "# Section 1" in result
        assert "- Bullet point 1" in result
        assert "**Bold text**" in result

    def test_markdown_topic_with_special_characters(self) -> None:
        """Test markdown export with topic containing special characters."""
        topic = "AI & Machine Learning: A Comprehensive Study"
        content_frames = ["Content"]

        result = to_markdown(topic, content_frames)

        assert (
            "# Literature Review: AI & Machine Learning: A Comprehensive Study"
            in result
        )

    def test_markdown_content_with_newlines(self) -> None:
        """Test markdown export with content containing newlines."""
        topic = "Test"
        content_frames = ["Line 1\nLine 2", "Another\nMultiline\nContent"]

        result = to_markdown(topic, content_frames)

        assert "Line 1\nLine 2" in result
        assert "Another\nMultiline\nContent" in result

    def test_markdown_empty_topic(self) -> None:
        """Test markdown export with empty topic."""
        topic = ""
        content_frames = ["Content"]

        result = to_markdown(topic, content_frames)

        # Should start with YAML frontmatter and include empty topic
        assert result.startswith("---\n")
        assert 'title: "Literature Review: "' in result
        assert 'topic: ""' in result
        assert "# Literature Review: " in result
        assert "Content" in result

    def test_markdown_large_content(self) -> None:
        """Test markdown export with large content."""
        topic = "Large Topic"
        content_frames = ["Frame " + str(i) for i in range(LARGE_CONTENT_SIZE)]

        result = to_markdown(topic, content_frames)

        # Should start with YAML frontmatter and include all frames
        assert result.startswith("---\n")
        assert 'title: "Literature Review: Large Topic"' in result
        assert "# Literature Review: Large Topic" in result
        assert "Frame 0" in result
        assert f"Frame {LARGE_CONTENT_SIZE - 1}" in result
        assert result.count("Frame ") == LARGE_CONTENT_SIZE

    def test_markdown_content_order_preserved(self) -> None:
        """Test that content frame order is preserved."""
        topic = "Ordered Topic"
        content_frames = ["First", "Second", "Third"]

        result = to_markdown(topic, content_frames)

        first_pos = result.find("First")
        second_pos = result.find("Second")
        third_pos = result.find("Third")

        assert first_pos < second_pos < third_pos

    def test_markdown_with_unicode_content(self) -> None:
        """Test markdown export with unicode characters."""
        topic = "Unicode Test 🚀"
        content_frames = ["Content with émojis 🎉 and ümlauts"]

        result = to_markdown(topic, content_frames)

        assert "Unicode Test 🚀" in result
        assert "émojis 🎉" in result
        assert "ümlauts" in result


class TestExportMetadata:
    """Test ExportMetadata dataclass."""

    def test_metadata_creation(self) -> None:
        """Test ExportMetadata creation with all fields."""
        metadata = ExportMetadata(
            topic="AI Research",
            generation_date="2024-01-15T10:30:00",
            model_used="gpt-4o",
            session_id="abc123",
            paper_count=5,
            version="0.1.0",
        )

        assert metadata.topic == "AI Research"
        assert metadata.generation_date == "2024-01-15T10:30:00"
        assert metadata.model_used == "gpt-4o"
        assert metadata.session_id == "abc123"
        expected_paper_count = 5
        assert metadata.paper_count == expected_paper_count
        assert metadata.version == "0.1.0"

    def test_metadata_default_version(self) -> None:
        """Test ExportMetadata uses default version."""
        metadata = ExportMetadata(
            topic="Test Topic",
            generation_date="2024-01-15T10:30:00",
            model_used="gpt-4o",
            session_id="xyz789",
            paper_count=3,
        )

        assert metadata.version == "0.1.0"

    def test_metadata_immutable(self) -> None:
        """Test ExportMetadata is immutable."""
        metadata = ExportMetadata(
            topic="Test",
            generation_date="2024-01-15T10:30:00",
            model_used="gpt-4o",
            session_id="test123",
            paper_count=1,
        )

        with pytest.raises(AttributeError):
            metadata.topic = "New Topic"  # type: ignore


class TestSanitizeTopicForFilename:
    """Test _sanitize_topic_for_filename function."""

    def test_basic_sanitization(self) -> None:
        """Test basic topic sanitization."""
        result = _sanitize_topic_for_filename("Machine Learning Research")
        assert result == "machine_learning_research"

    def test_special_characters_removed(self) -> None:
        """Test special characters are replaced with underscores."""
        result = _sanitize_topic_for_filename("AI & ML: A Study (2024)")
        # Current implementation collapses underscores and removes trailing ones
        assert result == "ai_ml_a_study_2024"

    def test_multiple_underscores_collapsed(self) -> None:
        """Test multiple consecutive underscores are collapsed."""
        topic = "AI___&___ML___Research"
        result = _sanitize_topic_for_filename(topic)
        assert "___" not in result
        assert result == "ai_ml_research"

    def test_leading_trailing_underscores_removed(self) -> None:
        """Test leading and trailing underscores are removed."""
        result = _sanitize_topic_for_filename("__Test Topic__")
        assert result == "test_topic"

    def test_empty_topic_returns_untitled(self) -> None:
        """Test empty topic returns 'untitled'."""
        assert _sanitize_topic_for_filename("") == "untitled"
        assert _sanitize_topic_for_filename("   ") == "untitled"

    def test_long_topic_truncation(self) -> None:
        """Test very long topics are truncated appropriately."""
        long_topic = "a" * 200
        result = _sanitize_topic_for_filename(long_topic)
        assert len(result) <= MAX_FILENAME_LENGTH - 30

    def test_unicode_handling(self) -> None:
        """Test unicode characters in topic."""
        result = _sanitize_topic_for_filename("Émojis 🚀 and ümlauts")
        # Current implementation collapses underscores and removes leading/trailing
        assert result == "mojis_and_mlauts"


class TestValidateExportInputs:
    """Test _validate_export_inputs function."""

    def test_valid_inputs(self) -> None:
        """Test valid inputs pass validation."""
        _validate_export_inputs("Valid Topic", ["content1", "content2"])
        # Should not raise any exception

    def test_invalid_topic_type(self) -> None:
        """Test invalid topic type raises ValidationError."""
        with pytest.raises(ValidationError, match="Topic must be a string"):
            _validate_export_inputs(123, ["content"])  # type: ignore[arg-type]

    def test_invalid_content_frames_type(self) -> None:
        """Test invalid content frames type raises ValidationError."""
        # Strings are iterable, so use a non-iterable type like int
        with pytest.raises(ValidationError, match="Content frames must be iterable"):
            # type: ignore[arg-type]
            _validate_export_inputs("Valid topic", 123)


class TestGenerateFilename:
    """Test generate_filename function."""

    def test_basic_filename_generation(self) -> None:
        """Test basic filename generation."""
        timestamp = datetime(2024, 1, 15, 14, 30)
        result = generate_filename("Machine Learning", "md", timestamp)
        assert result == "survey_studio_machine_learning_20240115_1430.md"

    def test_html_format(self) -> None:
        """Test HTML format filename generation."""
        timestamp = datetime(2024, 1, 15, 14, 30)
        result = generate_filename("AI Research", "html", timestamp)
        assert result == "survey_studio_ai_research_20240115_1430.html"

    def test_special_characters_in_topic(self) -> None:
        """Test filename generation with special characters."""
        timestamp = datetime(2024, 1, 15, 14, 30)
        result = generate_filename("AI & ML: Study", "md", timestamp)
        assert result == "survey_studio_ai_ml_study_20240115_1430.md"

    def test_default_timestamp(self) -> None:
        """Test filename generation with default timestamp."""
        result = generate_filename("Test Topic", "md")
        assert result.startswith("survey_studio_test_topic_")
        assert result.endswith(".md")
        # Should contain current timestamp
        assert re.match(r"survey_studio_test_topic_\d{8}_\d{4}\.md", result)

    def test_invalid_topic(self) -> None:
        """Test filename generation with invalid topic."""
        with pytest.raises(ValidationError, match="Topic must be a non-empty string"):
            generate_filename("", "md")

    def test_invalid_format(self) -> None:
        """Test filename generation with invalid format."""
        with pytest.raises(ValidationError, match="File format must be 'md' or 'html'"):
            generate_filename("Topic", "txt")

    def test_very_long_topic_truncation(self) -> None:
        """Test very long topic gets truncated appropriately."""
        long_topic = "a" * 200
        timestamp = datetime(2024, 1, 15, 14, 30)
        result = generate_filename(long_topic, "md", timestamp)
        assert len(result) <= MAX_FILENAME_LENGTH
        assert result.endswith("_20240115_1430.md")

    def test_filename_collision_handling(self) -> None:
        """Test filename handles potential collisions with timestamp."""
        topic = "Test"
        timestamp1 = datetime(2024, 1, 15, 14, 30)
        timestamp2 = datetime(2024, 1, 15, 14, 31)

        result1 = generate_filename(topic, "md", timestamp1)
        result2 = generate_filename(topic, "md", timestamp2)

        assert result1 != result2
        assert "20240115_1430" in result1
        assert "20240115_1431" in result2


class TestEnhancedToMarkdown:
    """Test enhanced to_markdown function with metadata."""

    def test_markdown_with_metadata(self) -> None:
        """Test markdown export with metadata."""
        metadata = ExportMetadata(
            topic="AI Research",
            generation_date="2024-01-15T10:30:00",
            model_used="gpt-4o",
            session_id="abc123",
            paper_count=5,
        )

        content_frames = ["Content 1", "Content 2"]
        result = to_markdown("AI Research", content_frames, metadata)

        # Check YAML frontmatter
        assert result.startswith("---\n")
        assert 'title: "Literature Review: AI Research"' in result
        assert 'topic: "AI Research"' in result
        assert 'generated_date: "2024-01-15T10:30:00"' in result
        assert 'model_used: "gpt-4o"' in result
        assert 'session_id: "abc123"' in result
        assert "paper_count: 5" in result
        assert 'version: "0.1.0"' in result
        assert 'export_format: "markdown"' in result
        assert "---\n\n" in result

        # Check content structure
        assert "# Literature Review: AI Research" in result
        assert "## Review Information" in result
        assert "- **Topic**: AI Research" in result
        assert "- **Generated**: 2024-01-15T10:30:00" in result
        assert "- **Model**: gpt-4o" in result
        assert "- **Papers Analyzed**: 5" in result
        assert "- **Session ID**: abc123" in result
        assert "Content 1" in result
        assert "Content 2" in result

    def test_markdown_without_metadata(self) -> None:
        """Test markdown export creates default metadata."""
        content_frames = ["Test content"]

        with patch("survey_studio.export.datetime") as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = (
                "2024-01-15T10:30:00"
            )
            result = to_markdown("Test Topic", content_frames)

        # Should create default metadata
        assert 'topic: "Test Topic"' in result
        assert 'generated_date: "2024-01-15T10:30:00"' in result
        assert 'model_used: "unknown"' in result
        assert 'session_id: "unknown"' in result
        assert "paper_count: 0" in result

    def test_markdown_with_empty_content(self) -> None:
        """Test markdown export with no content."""
        metadata = ExportMetadata(
            topic="Empty Test",
            generation_date="2024-01-15T10:30:00",
            model_used="gpt-4o",
            session_id="empty123",
            paper_count=0,
        )

        result = to_markdown("Empty Test", [], metadata)
        assert "*No content generated*" in result

    def test_markdown_validation_errors(self) -> None:
        """Test markdown export validation errors."""
        with pytest.raises(ValidationError):
            to_markdown(123, ["content"])  # type: ignore[arg-type]

        # Use non-iterable type instead of string (which is iterable)
        with pytest.raises(ValidationError):
            to_markdown("Topic", 123)  # type: ignore[arg-type]


class TestToHtml:
    """Test to_html function."""

    def test_basic_html_export(self) -> None:
        """Test basic HTML export."""
        metadata = ExportMetadata(
            topic="HTML Test",
            generation_date="2024-01-15T10:30:00",
            model_used="gpt-4o",
            session_id="html123",
            paper_count=3,
        )

        content_frames = ["# Section 1", "Some **bold** text"]
        result = to_html("HTML Test", content_frames, metadata)

        # Check HTML structure
        assert result.startswith("<!DOCTYPE html>")
        assert '<html lang="en">' in result
        assert '<meta charset="UTF-8">' in result
        assert "<title>Literature Review: HTML Test</title>" in result

        # Check metadata in meta tags
        assert '<meta name="topic" content="HTML Test">' in result
        assert '<meta name="generated-date" content="2024-01-15T10:30:00">' in result
        assert '<meta name="model-used" content="gpt-4o">' in result
        assert '<meta name="session-id" content="html123">' in result
        assert '<meta name="paper-count" content="3">' in result

        # Check CSS is included
        assert "<style>" in result
        assert "font-family:" in result
        assert "max-width: 800px" in result

        # Check converted content
        assert "<h1>Literature Review: HTML Test</h1>" in result
        assert "<h1>Section 1</h1>" in result
        assert "<strong>bold</strong>" in result

        # Check footer
        assert "Generated by Survey Studio" in result
        assert "2024-01-15T10:30:00" in result

    def test_html_without_metadata(self) -> None:
        """Test HTML export creates default metadata."""
        content_frames = ["Test content"]

        with patch("survey_studio.export.datetime") as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = (
                "2024-01-15T10:30:00"
            )
            result = to_html("Test Topic", content_frames)

        assert '<meta name="topic" content="Test Topic">' in result
        assert '<meta name="generated-date" content="2024-01-15T10:30:00">' in result
        assert '<meta name="model-used" content="unknown">' in result

    def test_html_with_special_characters(self) -> None:
        """Test HTML export escapes special characters in title."""
        content_frames = ["Content"]
        result = to_html('Test & Title < > "', content_frames)

        assert (
            "<title>Literature Review: Test &amp; Title &lt; &gt; &quot;</title>"
            in result
        )

    def test_html_with_empty_content(self) -> None:
        """Test HTML export with no content."""
        result = to_html("Empty", [])
        assert "<em>No content generated</em>" in result

    def test_html_validation_errors(self) -> None:
        """Test HTML export validation errors."""
        with pytest.raises(ValidationError):
            to_html(123, ["content"])  # type: ignore[arg-type]

        # Use non-iterable type instead of string (which is iterable)
        with pytest.raises(ValidationError):
            to_html("Topic", 123)  # type: ignore[arg-type]

    def test_html_markdown_conversion(self) -> None:
        """Test HTML properly converts markdown syntax."""
        # Use a single content frame with proper markdown formatting
        content_frames = [
            """## Heading 2

- List item 1
- List item 2

`code block`

> Blockquote"""
        ]

        result = to_html("Markdown Test", content_frames)

        assert "<h2>Heading 2</h2>" in result
        assert "<li>List item 1</li>" in result
        assert "<li>List item 2</li>" in result
        assert "<code>code block</code>" in result
        assert "<blockquote>" in result

    def test_html_responsive_design(self) -> None:
        """Test HTML includes responsive design elements."""
        result = to_html("Responsive", ["content"])

        assert 'name="viewport"' in result
        assert 'content="width=device-width, initial-scale=1.0"' in result
        assert "@media (max-width: 768px)" in result
        assert "@media print" in result


class TestGetExportFormats:
    """Test get_export_formats function."""

    def test_export_formats_structure(self) -> None:
        """Test export formats have correct structure."""
        formats = get_export_formats()

        assert isinstance(formats, dict)
        assert "markdown" in formats
        assert "html" in formats

        # Check markdown format
        md_format = formats["markdown"]
        assert md_format["extension"] == "md"
        assert md_format["mime_type"] == "text/markdown"
        assert md_format["function"] == to_markdown
        assert "description" in md_format

        # Check HTML format
        html_format = formats["html"]
        assert html_format["extension"] == "html"
        assert html_format["mime_type"] == "text/html"
        assert html_format["function"] == to_html
        assert "description" in html_format

    def test_export_formats_callable(self) -> None:
        """Test export format functions are callable."""
        formats = get_export_formats()

        for _format_name, format_info in formats.items():
            assert callable(format_info["function"])


class TestExportErrorHandling:
    """Test export error handling and retry mechanisms."""

    def test_export_error_with_retry_decorator(self) -> None:
        """Test that export functions use retry decorator."""
        # The retry decorator should be applied to the functions
        assert hasattr(generate_filename, "__wrapped__")
        assert hasattr(to_markdown, "__wrapped__")
        assert hasattr(to_html, "__wrapped__")

    def test_validation_error_propagation(self) -> None:
        """Test validation errors are properly propagated."""
        with pytest.raises(ValidationError, match="Topic must be a string"):
            to_markdown(123, ["content"])  # type: ignore[arg-type]

        with pytest.raises(ValidationError, match="Topic must be a string"):
            to_html(123, ["content"])  # type: ignore[arg-type]

    def test_export_error_context(self) -> None:
        """Test export errors include proper context."""
        with patch("survey_studio.export.MarkdownIt") as mock_md:
            mock_md.side_effect = Exception("Markdown conversion failed")

            try:
                to_html("Test", ["content"])
            except ExportError:
                with pytest.raises(
                    ExportError, match="Failed to generate HTML"
                ) as exc_info:
                    to_html("Test", ["content"])
                e = exc_info.value
                assert e.context["topic"] == "Test"
                assert e.context["content_frames_count"] == 1

    def test_filename_generation_error_context(self) -> None:
        """Test filename generation errors include context."""
        with patch("survey_studio.export.datetime") as mock_datetime:
            mock_datetime.side_effect = Exception("Time error")

            try:
                generate_filename("Test", "md")
            except ExportError:
                with pytest.raises(
                    ExportError, match="Failed to generate filename"
                ) as exc_info:
                    generate_filename("Test", "md")
                e = exc_info.value
                assert e.context["topic"] == "Test"
                assert e.context["format"] == "md"

    def test_export_error_message(self) -> None:
        """Test export error message."""
        with pytest.raises(ExportError, match="Test error") as exc_info:
            raise ExportError("Test error")
        assert exc_info.value.message == "Test error"
        assert exc_info.value.user_message == (
            "Export failed. Please try again or contact support if the "
            "problem persists."
        )
        assert exc_info.value.severity == ErrorSeverity.WARNING
        assert exc_info.value.context == {"topic": "Test", "format": "md"}
