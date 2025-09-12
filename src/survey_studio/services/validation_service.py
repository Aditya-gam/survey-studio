"""Validation service for Survey Studio API.

This module provides the ValidationService class that wraps validation
functions from the API module with proper error handling and type hints.
"""

from typing import TYPE_CHECKING

from survey_studio.api.functions import validate_review_request

if TYPE_CHECKING:
    from survey_studio.api.functions import ValidationResult


class ValidationService:
    """Service class for validation operations.

    Provides static methods that wrap validation functions from the API module
    with consistent error handling and return types.
    """

    @staticmethod
    def validate_request(topic: str, num_papers: int, model: str) -> "ValidationResult":
        """Validate a literature review request.

        Args:
            topic: Research topic to validate
            num_papers: Number of papers to review
            model: AI model to use for the review

        Returns:
            ValidationResult: Dict containing validation status and details

        Raises:
            ValidationError: If the request parameters are invalid
            ConfigurationError: If no AI providers are configured
        """
        return validate_review_request(topic, num_papers, model)
