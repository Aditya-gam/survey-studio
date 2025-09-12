"""Review service for Survey Studio API.

This module provides the ReviewService class that wraps review and session
functions from the API module with proper error handling and type hints.
"""

from typing import TYPE_CHECKING

from survey_studio.api.functions import initialize_session, run_review_with_fallback

if TYPE_CHECKING:
    from survey_studio.api.functions import ReviewResults


class ReviewService:
    """Service class for review operations.

    Provides static methods that wrap review functions from the API module
    with consistent error handling and return types.
    """

    @staticmethod
    def initialize_new_session() -> str:
        """Initialize a new review session.

        Returns:
            str: Unique session ID for tracking the review session

        Raises:
            No specific exceptions - this function initializes logging and session tracking
        """
        return initialize_session()

    @staticmethod
    def run_review(
        topic: str, num_papers: int, model: str, session_id: str | None = None
    ) -> "ReviewResults":
        """Run a literature review with fallback handling.

        Args:
            topic: Research topic to review
            num_papers: Number of papers to review
            model: AI model to use for the review
            session_id: Optional session ID for tracking (will create new if None)

        Returns:
            ReviewResults: Dict containing review results and metadata

        Raises:
            ValidationError: If inputs are invalid
            ConfigurationError: If no AI providers are configured
            ExternalServiceError: If external services fail
            LLMError: If AI model fails
            SurveyStudioError: If review process fails
        """
        return run_review_with_fallback(topic, num_papers, model, session_id)
