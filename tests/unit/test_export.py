"""Unit tests for export.py module."""

from __future__ import annotations

import pytest

from survey_studio.export import Paper, to_markdown


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
            {paper}

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

        assert result.startswith("# Literature Review: Machine Learning\n\n")
        assert "First frame content" in result
        assert "Second frame content" in result
        assert result.endswith("Second frame content\n")

    def test_markdown_with_empty_frames(self) -> None:
        """Test markdown export with empty content frames."""
        topic = "Test Topic"
        content_frames = []

        result = to_markdown(topic, content_frames)

        assert result == "# Literature Review: Test Topic\n\n\n"

    def test_markdown_with_single_frame(self) -> None:
        """Test markdown export with single content frame."""
        topic = "Single Topic"
        content_frames = ["Only content"]

        result = to_markdown(topic, content_frames)

        expected = "# Literature Review: Single Topic\n\nOnly content\n"
        assert result == expected

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

        assert result == "# Literature Review: \n\nContent\n"

    def test_markdown_large_content(self) -> None:
        """Test markdown export with large content."""
        topic = "Large Topic"
        content_frames = ["Frame " + str(i) for i in range(100)]

        result = to_markdown(topic, content_frames)

        assert result.startswith("# Literature Review: Large Topic\n\n")
        assert "Frame 0" in result
        assert "Frame 99" in result
        assert result.count("Frame ") == 100

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
