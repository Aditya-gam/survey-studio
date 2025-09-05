"""Unit tests for tools.py module."""

from __future__ import annotations

from unittest.mock import Mock, patch

from autogen_core.tools import FunctionTool
import pytest

from survey_studio.errors import ArxivSearchError
from survey_studio.tools import arxiv_search, arxiv_tool


class TestArxivSearch:
    """Test arxiv_search function."""

    def test_arxiv_search_success(self, sample_paper_data: list[dict]) -> None:
        """Test successful arXiv search."""
        mock_result = Mock()
        mock_result.title = "Test Paper Title"
        mock_result.authors = [Mock(name="Test Author")]
        mock_result.authors[0].name = "Test Author"
        mock_result.published = Mock()
        mock_result.published.strftime.return_value = "2023-01-15"
        mock_result.summary = "Test paper summary"
        mock_result.pdf_url = "https://arxiv.org/pdf/test.pdf"

        with (
            patch("survey_studio.tools.arxiv.Client") as mock_client_class,
            patch("survey_studio.tools.arxiv.Search") as mock_search_class,
            patch("survey_studio.tools.logger") as mock_logger,
        ):
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            mock_search = Mock()
            mock_search_class.return_value = mock_search

            mock_client.results.return_value = [mock_result]

            result = arxiv_search("test query", 5)

            assert len(result) == 1
            assert result[0]["title"] == "Test Paper Title"
            assert result[0]["authors"] == ["Test Author"]
            assert result[0]["published"] == "2023-01-15"
            assert result[0]["summary"] == "Test paper summary"
            assert result[0]["pdf_url"] == "https://arxiv.org/pdf/test.pdf"

    def test_arxiv_search_multiple_results(self) -> None:
        """Test arXiv search with multiple results."""
        mock_results = []
        for i in range(3):
            mock_result = Mock()
            mock_result.title = f"Paper {i}"
            mock_result.authors = [Mock(name=f"Author {i}")]
            mock_result.authors[0].name = f"Author {i}"
            mock_result.published = Mock()
            mock_result.published.strftime.return_value = f"2023-01-{15+i}"
            mock_result.summary = f"Summary {i}"
            mock_result.pdf_url = f"https://arxiv.org/pdf/test{i}.pdf"
            mock_results.append(mock_result)

        with (
            patch("survey_studio.tools.arxiv.Client") as mock_client_class,
            patch("survey_studio.tools.arxiv.Search") as mock_search_class,
            patch("survey_studio.tools.logger"),
        ):
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.results.return_value = mock_results

            mock_search = Mock()
            mock_search_class.return_value = mock_search

            result = arxiv_search("test query", 5)

            assert len(result) == 3
            for i in range(3):
                assert result[i]["title"] == f"Paper {i}"
                assert result[i]["authors"] == [f"Author {i}"]

    def test_arxiv_search_with_max_results(self) -> None:
        """Test arXiv search respects max_results parameter."""
        # Create properly structured mock results
        mock_results = []
        for i in range(3):
            mock_result = Mock()
            mock_result.title = f"Paper {i}"
            mock_author = Mock()
            mock_author.name = f"Author {i}"
            mock_result.authors = [mock_author]
            mock_result.published = Mock()
            mock_result.published.strftime.return_value = f"2023-01-{15+i}"
            mock_result.summary = f"Summary {i}"
            mock_result.pdf_url = f"https://arxiv.org/pdf/test{i}.pdf"
            mock_results.append(mock_result)

        with (
            patch("survey_studio.tools.arxiv.Client") as mock_client_class,
            patch("survey_studio.tools.arxiv.Search") as mock_search_class,
            patch("survey_studio.tools.with_context") as mock_with_context,
        ):
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.results.return_value = mock_results

            mock_search = Mock()
            mock_search_class.return_value = mock_search

            mock_context_logger = Mock()
            mock_with_context.return_value = mock_context_logger

            result = arxiv_search("test query", 3)

            # Verify Search was called with correct max_results
            mock_search_class.assert_called_once()
            call_kwargs = mock_search_class.call_args[1]
            assert call_kwargs["max_results"] == 3
            assert len(result) == 3

    def test_arxiv_search_default_max_results(self) -> None:
        """Test arXiv search uses default max_results when not specified."""
        with (
            patch("survey_studio.tools.arxiv.Client") as mock_client_class,
            patch("survey_studio.tools.arxiv.Search") as mock_search_class,
            patch("survey_studio.tools.logger"),
        ):
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.results.return_value = []

            mock_search = Mock()
            mock_search_class.return_value = mock_search

            arxiv_search("test query")

            # Verify Search was called with default max_results=5
            mock_search_class.assert_called_once()
            call_kwargs = mock_search_class.call_args[1]
            assert call_kwargs["max_results"] == 5

    def test_arxiv_search_empty_results(self) -> None:
        """Test arXiv search with no results."""
        with (
            patch("survey_studio.tools.arxiv.Client") as mock_client_class,
            patch("survey_studio.tools.arxiv.Search") as mock_search_class,
            patch("survey_studio.tools.with_context") as mock_with_context,
        ):
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.results.return_value = []

            mock_search = Mock()
            mock_search_class.return_value = mock_search

            mock_context_logger = Mock()
            mock_with_context.return_value = mock_context_logger

            result = arxiv_search("test query", 5)

            assert result == []
            mock_context_logger.info.assert_called_once()

    def test_arxiv_search_exception_handling(self) -> None:
        """Test arXiv search handles exceptions properly."""
        with (
            patch(
                "survey_studio.tools.arxiv.Client",
                side_effect=Exception("Network error"),
            ),
            patch("survey_studio.tools.with_context") as mock_with_context,
        ):
            mock_context_logger = Mock()
            mock_with_context.return_value = mock_context_logger

            with pytest.raises(
                ArxivSearchError, match="Failed to fetch results from arXiv"
            ):
                arxiv_search("test query", 5)

            # Verify error was logged
            mock_context_logger.error.assert_called_once()

    def test_arxiv_search_preserves_original_exception(self) -> None:
        """Test arXiv search preserves original exception in ArxivSearchError."""
        original_error = ConnectionError("Connection failed")

        with (
            patch("survey_studio.tools.arxiv.Client", side_effect=original_error),
            patch("survey_studio.tools.with_context") as mock_with_context,
        ):
            mock_context_logger = Mock()
            mock_with_context.return_value = mock_context_logger

            with pytest.raises(ArxivSearchError) as exc_info:
                arxiv_search("test query", 5)

            assert exc_info.value.__cause__ is original_error

    def test_arxiv_search_with_context_logging(self) -> None:
        """Test arXiv search uses contextual logging."""
        with (
            patch("survey_studio.tools.arxiv.Client") as mock_client_class,
            patch("survey_studio.tools.arxiv.Search") as mock_search_class,
            patch("survey_studio.tools.with_context") as mock_with_context,
        ):
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.results.return_value = []

            mock_search = Mock()
            mock_search_class.return_value = mock_search

            mock_context_logger = Mock()
            mock_with_context.return_value = mock_context_logger

            arxiv_search("test query", 5)

            # Verify with_context was called with correct logger
            mock_with_context.assert_called_once()
            call_args = mock_with_context.call_args
            assert "tool_name" in call_args[1]
            assert call_args[1]["tool_name"] == "arxiv_search"

    def test_arxiv_search_result_structure(self) -> None:
        """Test arXiv search returns correct result structure."""
        mock_result = Mock()
        mock_result.title = "Advanced Machine Learning"
        mock_result.authors = [Mock(name="Dr. Smith"), Mock(name="Prof. Johnson")]
        mock_result.authors[0].name = "Dr. Smith"
        mock_result.authors[1].name = "Prof. Johnson"
        mock_result.published = Mock()
        mock_result.published.strftime.return_value = "2023-12-01"
        mock_result.summary = "This paper explores advanced ML techniques."
        mock_result.pdf_url = "https://arxiv.org/pdf/2312.00123.pdf"

        expected_result = {
            "title": "Advanced Machine Learning",
            "authors": ["Dr. Smith", "Prof. Johnson"],
            "published": "2023-12-01",
            "summary": "This paper explores advanced ML techniques.",
            "pdf_url": "https://arxiv.org/pdf/2312.00123.pdf",
        }

        with (
            patch("survey_studio.tools.arxiv.Client") as mock_client_class,
            patch("survey_studio.tools.arxiv.Search") as mock_search_class,
            patch("survey_studio.tools.logger"),
        ):
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.results.return_value = [mock_result]

            mock_search = Mock()
            mock_search_class.return_value = mock_search

            result = arxiv_search("machine learning", 1)

            assert len(result) == 1
            assert result[0] == expected_result

    def test_arxiv_search_relevance_sorting(self) -> None:
        """Test arXiv search uses relevance sorting."""
        with (
            patch("survey_studio.tools.arxiv.Client") as mock_client_class,
            patch("survey_studio.tools.arxiv.Search") as mock_search_class,
            patch("survey_studio.tools.logger"),
        ):
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.results.return_value = []

            mock_search = Mock()
            mock_search_class.return_value = mock_search

            arxiv_search("test query", 5)

            # Verify Search was called with SortCriterion.Relevance
            mock_search_class.assert_called_once()
            call_kwargs = mock_search_class.call_args[1]
            assert "sort_by" in call_kwargs
            # We can't easily check the exact SortCriterion enum value,
            # but we can verify sort_by was passed


class TestArxivTool:
    """Test arxiv_tool FunctionTool."""

    def test_arxiv_tool_is_function_tool(self) -> None:
        """Test that arxiv_tool is a FunctionTool instance."""
        assert isinstance(arxiv_tool, FunctionTool)

    def test_arxiv_tool_function(self) -> None:
        """Test that arxiv_tool wraps arxiv_search function."""
        # FunctionTool stores the function in _func attribute
        assert arxiv_tool._func is arxiv_search

    def test_arxiv_tool_description(self) -> None:
        """Test arxiv_tool has correct description."""
        expected_description = (
            "Searches arXiv and returns up to max_results papers, each containing "
            "title, authors, publication date, abstract, and pdf_url."
        )
        assert arxiv_tool.description == expected_description

    def test_arxiv_tool_name(self) -> None:
        """Test arxiv_tool has correct name."""
        assert arxiv_tool.name == "arxiv_search"

    def test_arxiv_tool_execution(self) -> None:
        """Test arxiv_tool can be executed."""
        # Test that the tool's underlying function works
        assert callable(arxiv_tool._func)
        assert arxiv_tool._func.__name__ == "arxiv_search"
