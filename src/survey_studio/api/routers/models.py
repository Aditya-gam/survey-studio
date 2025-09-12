"""Models router for Survey Studio API.

Provides information about available AI models organized by provider.
"""

from fastapi import APIRouter

from survey_studio.schemas import ModelsResponse

router = APIRouter()


@router.get(
    "/models",
    response_model=ModelsResponse,
    summary="Get available AI models",
    description="Returns a list of available AI models organized by provider.",
    tags=["models"],
)
async def get_models() -> ModelsResponse:
    """Get available AI models by provider.

    Calls the existing get_available_models function and converts the result
    to a proper Pydantic response model.

    Returns:
        ModelsResponse: Available models organized by provider
    """
    # Import here to avoid circular imports
    from survey_studio.api import get_available_models  # noqa: PLC0415

    models_data = get_available_models()

    return ModelsResponse(models=models_data)
