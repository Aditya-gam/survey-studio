"""Reviews router for Survey Studio API.

Provides endpoints for running literature reviews.
"""

from fastapi import APIRouter

from survey_studio.schemas import ReviewResponse, ReviewValidateRequest
from survey_studio.services.review_service import ReviewService

router = APIRouter()


@router.post(
    "/reviews",
    response_model=ReviewResponse,
    summary="Run literature review",
    description="Runs a complete literature review for the given topic and parameters.",
    tags=["reviews"],
)
async def run_review(request: ReviewValidateRequest) -> ReviewResponse:
    """Run a literature review.

    Initializes a new session and runs a complete literature review process
    for the specified topic, number of papers, and AI model.

    Args:
        request: Review request containing topic, num_papers, and model

    Returns:
        ReviewResponse: Review status and results

    Raises:
        ValidationError: If inputs are invalid (handled as 400)
        ConfigurationError: If no AI providers are configured (handled as 503)
        ExternalServiceError: If external services fail (handled as 502)
        LLMError: If AI model fails (handled as 502)
        SurveyStudioError: If review process fails (handled as 500)
    """
    # Initialize a new session
    session_id = ReviewService.initialize_new_session()

    # Run the review
    review_result = ReviewService.run_review(
        topic=request.topic,
        num_papers=request.num_papers,
        model=request.model,
        session_id=session_id,
    )

    return ReviewResponse(status="completed", results=review_result["results"])
