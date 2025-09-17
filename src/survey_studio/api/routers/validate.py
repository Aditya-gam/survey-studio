"""Validation router for Survey Studio API.

Provides validation endpoints for literature review requests.
"""

from typing import Any, cast

from fastapi import APIRouter

from survey_studio.schemas import ReviewValidateRequest, ValidateResponse
from survey_studio.services.validation_service import ValidationService

router = APIRouter()


@router.post(
    "/validate",
    response_model=ValidateResponse,
    summary="Validate literature review request",
    description="Validates the parameters for a literature review request before processing.",
    tags=["validation"],
)
async def validate_review(request: ReviewValidateRequest) -> ValidateResponse:
    """Validate a literature review request.

    Validates the topic and number of papers to ensure they meet the requirements
    for processing a literature review. The system automatically selects the best
    available AI provider using the fallback order: TogetherAI → Gemini → Perplexity → OpenAI

    Args:
        request: Review validation request containing topic and num_papers

    Returns:
        ValidateResponse: Validation status and results

    Raises:
        ValidationError: If request parameters are invalid (handled as 400)
        ConfigurationError: If no AI providers are configured (handled as 503)
    """
    validation_result = ValidationService.validate_request(
        topic=request.topic, num_papers=request.num_papers
    )

    return ValidateResponse(status="completed", results=cast(dict[str, Any], validation_result))
