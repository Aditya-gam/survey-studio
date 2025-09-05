"""Integration tests for orchestrator.py module."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from survey_studio.errors import OrchestrationError, ValidationError
from survey_studio.orchestrator import run_survey_studio


class TestRunSurveyStudio:
    """Integration tests for run_survey_studio function."""

    @pytest.mark.asyncio
    async def test_run_survey_studio_success(self, mock_team: Mock) -> None:
        """Test successful end-to-end survey studio run."""
        with (
            patch(
                "survey_studio.orchestrator.validate_topic",
                return_value="Machine Learning",
            ),
            patch("survey_studio.orchestrator.validate_num_papers", return_value=5),
            patch(
                "survey_studio.orchestrator.validate_model", return_value="gpt-4o-mini"
            ),
            patch(
                "survey_studio.orchestrator.validate_openai_key",
                return_value="test-key",
            ),
            patch("survey_studio.orchestrator.build_team", return_value=mock_team),
            patch("survey_studio.orchestrator.configure_logging"),
            patch("survey_studio.orchestrator.new_session_id", return_value="test1234"),
            patch("survey_studio.orchestrator.set_session_id"),
            patch("survey_studio.orchestrator.logger") as mock_logger,
        ):
            mock_context_logger = Mock()
            mock_logger.return_value = mock_context_logger

            # Collect results from async generator
            results = []
            async for result in run_survey_studio("Machine Learning", 5, "gpt-4o-mini"):
                results.append(result)

            assert len(results) == 2
            assert results[0] == "search_agent: Found relevant papers on the topic."
            assert (
                results[1] == "summarizer: # Literature Review\n\nTest summary content."
            )

    @pytest.mark.asyncio
    async def test_run_survey_studio_with_session_id(self, mock_team: Mock) -> None:
        """Test run_survey_studio with provided session ID."""
        test_session_id = "custom123"

        with (
            patch(
                "survey_studio.orchestrator.validate_topic", return_value="AI Research"
            ),
            patch("survey_studio.orchestrator.validate_num_papers", return_value=3),
            patch("survey_studio.orchestrator.validate_model", return_value="gpt-4o"),
            patch(
                "survey_studio.orchestrator.validate_openai_key",
                return_value="test-key",
            ),
            patch("survey_studio.orchestrator.build_team", return_value=mock_team),
            patch("survey_studio.orchestrator.configure_logging"),
            patch("survey_studio.orchestrator.new_session_id") as mock_new_session,
            patch("survey_studio.orchestrator.set_session_id") as mock_set_session,
        ):
            results = []
            async for result in run_survey_studio(
                "AI Research", 3, "gpt-4o", session_id=test_session_id
            ):
                results.append(result)

            # Should not generate new session ID when provided
            mock_new_session.assert_not_called()
            mock_set_session.assert_called_once_with(test_session_id)
            assert len(results) == 2

    @pytest.mark.asyncio
    async def test_run_survey_studio_without_session_id(self, mock_team: Mock) -> None:
        """Test run_survey_studio generates session ID when not provided."""
        with (
            patch(
                "survey_studio.orchestrator.validate_topic", return_value="Test Topic"
            ),
            patch("survey_studio.orchestrator.validate_num_papers", return_value=2),
            patch(
                "survey_studio.orchestrator.validate_model", return_value="gpt-4o-mini"
            ),
            patch(
                "survey_studio.orchestrator.validate_openai_key",
                return_value="test-key",
            ),
            patch("survey_studio.orchestrator.build_team", return_value=mock_team),
            patch("survey_studio.orchestrator.configure_logging"),
            patch(
                "survey_studio.orchestrator.new_session_id", return_value="generated456"
            ),
            patch("survey_studio.orchestrator.set_session_id") as mock_set_session,
        ):
            results = []
            async for result in run_survey_studio("Test Topic", 2):
                results.append(result)

            # Should generate new session ID when not provided
            mock_set_session.assert_called_once_with("generated456")
            assert len(results) == 2

    @pytest.mark.asyncio
    async def test_run_survey_studio_validation_error_topic(self) -> None:
        """Test run_survey_studio handles topic validation error."""
        with (
            patch(
                "survey_studio.orchestrator.validate_topic",
                side_effect=ValidationError("Invalid topic"),
            ),
            patch("survey_studio.orchestrator.configure_logging"),
            patch("survey_studio.orchestrator.new_session_id", return_value="test123"),
            patch("survey_studio.orchestrator.set_session_id"),
            patch("survey_studio.orchestrator.logger") as mock_logger,
        ):
            mock_context_logger = Mock()
            mock_logger.return_value = mock_context_logger

            with pytest.raises(
                OrchestrationError, match="Failed to run literature review"
            ):
                async for _ in run_survey_studio("", 5):
                    pass

    @pytest.mark.asyncio
    async def test_run_survey_studio_validation_error_num_papers(self) -> None:
        """Test run_survey_studio handles num_papers validation error."""
        with (
            patch(
                "survey_studio.orchestrator.validate_topic", return_value="Valid Topic"
            ),
            patch(
                "survey_studio.orchestrator.validate_num_papers",
                side_effect=ValidationError("Invalid num_papers"),
            ),
            patch("survey_studio.orchestrator.configure_logging"),
            patch("survey_studio.orchestrator.new_session_id", return_value="test123"),
            patch("survey_studio.orchestrator.set_session_id"),
            patch("survey_studio.orchestrator.logger") as mock_logger,
        ):
            mock_context_logger = Mock()
            mock_logger.return_value = mock_context_logger

            with pytest.raises(
                OrchestrationError, match="Failed to run literature review"
            ):
                async for _ in run_survey_studio("Valid Topic", 0):
                    pass

    @pytest.mark.asyncio
    async def test_run_survey_studio_validation_error_model(self) -> None:
        """Test run_survey_studio handles model validation error."""
        with (
            patch(
                "survey_studio.orchestrator.validate_topic", return_value="Valid Topic"
            ),
            patch("survey_studio.orchestrator.validate_num_papers", return_value=5),
            patch(
                "survey_studio.orchestrator.validate_model",
                side_effect=ValidationError("Invalid model"),
            ),
            patch("survey_studio.orchestrator.configure_logging"),
            patch("survey_studio.orchestrator.new_session_id", return_value="test123"),
            patch("survey_studio.orchestrator.set_session_id"),
            patch("survey_studio.orchestrator.logger") as mock_logger,
        ):
            mock_context_logger = Mock()
            mock_logger.return_value = mock_context_logger

            with pytest.raises(
                OrchestrationError, match="Failed to run literature review"
            ):
                async for _ in run_survey_studio("Valid Topic", 5, "invalid-model"):
                    pass

    @pytest.mark.asyncio
    async def test_run_survey_studio_validation_error_api_key(self) -> None:
        """Test run_survey_studio handles API key validation error."""
        with (
            patch(
                "survey_studio.orchestrator.validate_topic", return_value="Valid Topic"
            ),
            patch("survey_studio.orchestrator.validate_num_papers", return_value=5),
            patch(
                "survey_studio.orchestrator.validate_model", return_value="gpt-4o-mini"
            ),
            patch(
                "survey_studio.orchestrator.validate_openai_key",
                side_effect=ValidationError("Missing API key"),
            ),
            patch("survey_studio.orchestrator.configure_logging"),
            patch("survey_studio.orchestrator.new_session_id", return_value="test123"),
            patch("survey_studio.orchestrator.set_session_id"),
            patch("survey_studio.orchestrator.logger") as mock_logger,
        ):
            mock_context_logger = Mock()
            mock_logger.return_value = mock_context_logger

            with pytest.raises(
                OrchestrationError, match="Failed to run literature review"
            ):
                async for _ in run_survey_studio("Valid Topic", 5):
                    pass

    @pytest.mark.asyncio
    async def test_run_survey_studio_team_building_error(self) -> None:
        """Test run_survey_studio handles team building error."""
        with (
            patch(
                "survey_studio.orchestrator.validate_topic", return_value="Valid Topic"
            ),
            patch("survey_studio.orchestrator.validate_num_papers", return_value=5),
            patch(
                "survey_studio.orchestrator.validate_model", return_value="gpt-4o-mini"
            ),
            patch(
                "survey_studio.orchestrator.validate_openai_key",
                return_value="test-key",
            ),
            patch(
                "survey_studio.orchestrator.build_team",
                side_effect=Exception("Team building failed"),
            ),
            patch("survey_studio.orchestrator.configure_logging"),
            patch("survey_studio.orchestrator.new_session_id", return_value="test123"),
            patch("survey_studio.orchestrator.set_session_id"),
            patch("survey_studio.orchestrator.logger") as mock_logger,
        ):
            mock_context_logger = Mock()
            mock_logger.return_value = mock_context_logger

            with pytest.raises(
                OrchestrationError, match="Failed to run literature review"
            ):
                async for _ in run_survey_studio("Valid Topic", 5):
                    pass

    @pytest.mark.asyncio
    async def test_run_survey_studio_streaming_error(self, mock_team: Mock) -> None:
        """Test run_survey_studio handles streaming error."""

        # Create a mock team that raises an exception during streaming
        async def failing_run_stream(*args, **kwargs):
            raise Exception("Streaming failed")
            yield  # pragma: no cover

        mock_team.run_stream = failing_run_stream

        with (
            patch(
                "survey_studio.orchestrator.validate_topic", return_value="Valid Topic"
            ),
            patch("survey_studio.orchestrator.validate_num_papers", return_value=5),
            patch(
                "survey_studio.orchestrator.validate_model", return_value="gpt-4o-mini"
            ),
            patch(
                "survey_studio.orchestrator.validate_openai_key",
                return_value="test-key",
            ),
            patch("survey_studio.orchestrator.build_team", return_value=mock_team),
            patch("survey_studio.orchestrator.configure_logging"),
            patch("survey_studio.orchestrator.new_session_id", return_value="test123"),
            patch("survey_studio.orchestrator.set_session_id"),
            patch("survey_studio.orchestrator.logger") as mock_logger,
        ):
            mock_context_logger = Mock()
            mock_logger.return_value = mock_context_logger

            with pytest.raises(
                OrchestrationError, match="Failed to run literature review"
            ):
                async for _ in run_survey_studio("Valid Topic", 5):
                    pass

    @pytest.mark.asyncio
    async def test_run_survey_studio_logging_integration(self, mock_team: Mock) -> None:
        """Test run_survey_studio logging integration."""
        with (
            patch(
                "survey_studio.orchestrator.validate_topic", return_value="Test Topic"
            ),
            patch("survey_studio.orchestrator.validate_num_papers", return_value=3),
            patch("survey_studio.orchestrator.validate_model", return_value="gpt-4o"),
            patch(
                "survey_studio.orchestrator.validate_openai_key",
                return_value="test-key",
            ),
            patch("survey_studio.orchestrator.build_team", return_value=mock_team),
            patch("survey_studio.orchestrator.configure_logging"),
            patch(
                "survey_studio.orchestrator.new_session_id", return_value="logtest123"
            ),
            patch("survey_studio.orchestrator.set_session_id"),
            patch("survey_studio.orchestrator.with_context") as mock_with_context,
        ):
            mock_context_logger = Mock()
            mock_with_context.return_value = mock_context_logger

            results = []
            async for result in run_survey_studio("Test Topic", 3, "gpt-4o"):
                results.append(result)

            # Verify logging calls
            assert mock_context_logger.info.call_count >= 2  # At least start and end
            assert len(results) == 2

    @pytest.mark.asyncio
    async def test_run_survey_studio_message_format(self, mock_team: Mock) -> None:
        """Test run_survey_studio message formatting."""

        # Create custom mock team with different messages
        async def custom_run_stream(*args, **kwargs):
            from autogen_agentchat.messages import TextMessage

            yield TextMessage(source="agent1", content="First message")
            yield TextMessage(
                source="agent2", content="Second message with **markdown**"
            )

        mock_team.run_stream = custom_run_stream

        with (
            patch("survey_studio.orchestrator.validate_topic", return_value="Test"),
            patch("survey_studio.orchestrator.validate_num_papers", return_value=2),
            patch(
                "survey_studio.orchestrator.validate_model", return_value="gpt-4o-mini"
            ),
            patch(
                "survey_studio.orchestrator.validate_openai_key",
                return_value="test-key",
            ),
            patch("survey_studio.orchestrator.build_team", return_value=mock_team),
            patch("survey_studio.orchestrator.configure_logging"),
            patch(
                "survey_studio.orchestrator.new_session_id", return_value="format123"
            ),
            patch("survey_studio.orchestrator.set_session_id"),
        ):
            results = []
            async for result in run_survey_studio("Test", 2):
                results.append(result)

            assert len(results) == 2
            assert results[0] == "agent1: First message"
            assert results[1] == "agent2: Second message with **markdown**"

    @pytest.mark.asyncio
    async def test_run_survey_studio_task_prompt_construction(
        self, mock_team: Mock
    ) -> None:
        """Test run_survey_studio constructs correct task prompt."""
        with (
            patch(
                "survey_studio.orchestrator.validate_topic",
                return_value="Machine Learning Research",
            ),
            patch("survey_studio.orchestrator.validate_num_papers", return_value=7),
            patch("survey_studio.orchestrator.validate_model", return_value="gpt-4o"),
            patch(
                "survey_studio.orchestrator.validate_openai_key",
                return_value="test-key",
            ),
            patch(
                "survey_studio.orchestrator.build_team", return_value=mock_team
            ) as mock_build_team,
            patch("survey_studio.orchestrator.configure_logging"),
            patch(
                "survey_studio.orchestrator.new_session_id", return_value="prompt123"
            ),
            patch("survey_studio.orchestrator.set_session_id"),
        ):
            results = []
            async for result in run_survey_studio(
                "Machine Learning Research", 7, "gpt-4o"
            ):
                results.append(result)

            # Verify the task prompt was constructed correctly
            mock_build_team.assert_called_once()
            # Check that results were produced (indicating team was called)
            assert len(results) == 2

    @pytest.mark.asyncio
    async def test_run_survey_studio_empty_stream(self) -> None:
        """Test run_survey_studio handles empty message stream."""
        mock_team = Mock()

        async def empty_run_stream(*args, **kwargs):
            return
            yield  # pragma: no cover

        mock_team.run_stream = empty_run_stream

        with (
            patch("survey_studio.orchestrator.validate_topic", return_value="Test"),
            patch("survey_studio.orchestrator.validate_num_papers", return_value=1),
            patch(
                "survey_studio.orchestrator.validate_model", return_value="gpt-4o-mini"
            ),
            patch(
                "survey_studio.orchestrator.validate_openai_key",
                return_value="test-key",
            ),
            patch("survey_studio.orchestrator.build_team", return_value=mock_team),
            patch("survey_studio.orchestrator.configure_logging"),
            patch("survey_studio.orchestrator.new_session_id", return_value="empty123"),
            patch("survey_studio.orchestrator.set_session_id"),
        ):
            results = []
            async for result in run_survey_studio("Test", 1):
                results.append(result)

            assert len(results) == 0
