"""Shared pytest fixtures and configuration for Survey Studio tests."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any
from unittest.mock import Mock

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

from autogen_agentchat.messages import TextMessage
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient
import pytest


@pytest.fixture
def mock_openai_client() -> Mock:
    """Mock OpenAI chat completion client."""
    client = Mock(spec=OpenAIChatCompletionClient)
    # Add model_info that AutoGen expects
    client.model_info = {"family": "gpt-4", "function_calling": True}
    return client


@pytest.fixture
def mock_arxiv_client() -> Mock:
    """Mock arXiv client."""
    return Mock()


@pytest.fixture
def mock_team() -> Mock:
    """Mock AutoGen team with async streaming support."""
    team = Mock(spec=RoundRobinGroupChat)

    async def mock_run_stream(*, task: str) -> AsyncGenerator[TextMessage, None]:  # noqa: ARG001
        """Mock streaming that yields test messages."""
        messages = [
            TextMessage(
                source="search_agent", content="Found relevant papers on the topic."
            ),
            TextMessage(
                source="summarizer",
                content="# Literature Review\n\nTest summary content.",
            ),
        ]
        for msg in messages:
            yield msg

    team.run_stream = mock_run_stream
    return team


@pytest.fixture
def sample_paper_data() -> list[dict[str, Any]]:
    """Sample paper data for testing."""
    return [
        {
            "title": "Test Paper Title",
            "authors": ["Author One", "Author Two"],
            "published": "2023-01-15",
            "summary": "This is a test paper summary.",
            "pdf_url": "https://arxiv.org/pdf/test.pdf",
        },
        {
            "title": "Another Test Paper",
            "authors": ["Author Three"],
            "published": "2023-02-20",
            "summary": "Another test summary.",
            "pdf_url": "https://arxiv.org/pdf/test2.pdf",
        },
    ]


@pytest.fixture
def sample_session_id() -> str:
    """Sample session ID for testing."""
    return "test1234"


@pytest.fixture(autouse=True)
def mock_env_vars() -> Generator[None, None, None]:  # noqa: PT004
    """Mock environment variables for testing."""
    original_env = dict(os.environ)

    # Set test environment variables
    os.environ["OPENAI_API_KEY"] = (
        "sk-test1234567890abcdef1234567890abcdef1234567890"  # pragma: allowlist secret
    )

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def valid_topic() -> str:
    """Valid topic for testing."""
    return "Machine Learning in Healthcare"


@pytest.fixture
def invalid_topic_empty() -> str:
    """Invalid empty topic."""
    return ""


@pytest.fixture
def invalid_topic_whitespace() -> str:
    """Invalid whitespace-only topic."""
    return "   \t\n  "


@pytest.fixture
def invalid_topic_too_long() -> str:
    """Invalid topic exceeding max length."""
    return "A" * 201  # MAX_TOPIC_LENGTH + 1


@pytest.fixture
def valid_num_papers() -> int:
    """Valid number of papers."""
    return 5


@pytest.fixture
def invalid_num_papers_zero() -> int:
    """Invalid zero papers."""
    return 0


@pytest.fixture
def invalid_num_papers_negative() -> int:
    """Invalid negative papers."""
    return -1


@pytest.fixture
def invalid_num_papers_too_large() -> int:
    """Invalid papers exceeding max."""
    return 11  # MAX_NUM_PAPERS + 1


@pytest.fixture
def valid_model() -> str:
    """Valid model name."""
    return "gpt-4o-mini"


@pytest.fixture
def invalid_model() -> str:
    """Invalid model name."""
    return "invalid-model"


@pytest.fixture
def test_text_with_whitespace() -> str:
    """Test text with various whitespace characters."""
    return "  Test\ttext\nwith   multiple   spaces  \n\t"


@pytest.fixture
def test_text_with_control_chars() -> str:
    """Test text with control characters."""
    return "Test\x00text\x01with\x02control\x03chars"


@pytest.fixture
def test_text_unicode() -> str:
    """Test text with unicode characters."""
    return "Test text with émojis 🚀 and ümlauts"
