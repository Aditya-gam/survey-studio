"""Providers router for Survey Studio API.

Provides information about available AI providers and their configuration.
"""

from fastapi import APIRouter

from survey_studio.schemas import ProviderInfo, ProviderResponse

router = APIRouter()


@router.get(
    "/providers",
    response_model=ProviderResponse,
    summary="Get AI provider status",
    description="Returns information about available AI providers and their configuration.",
    tags=["providers"],
)
async def get_providers() -> ProviderResponse:
    """Get AI provider status and configuration.

    Calls the existing get_provider_status function and converts the result
    to a proper Pydantic response model.

    Returns:
        ProviderResponse: Current provider status and configuration
    """
    # Import here to avoid circular imports
    from survey_studio.api import get_provider_status  # noqa: PLC0415

    provider_data = get_provider_status()

    provider_info_list = [
        ProviderInfo(
            name=provider["name"],
            model=provider["model"],
            priority=provider["priority"],
            free_tier_rpm=provider["free_tier_rpm"],
            free_tier_tpm=provider["free_tier_tpm"],
        )
        for provider in provider_data["providers"]
    ]

    return ProviderResponse(
        available_count=provider_data["available_count"],
        best_provider=provider_data["best_provider"],
        providers=provider_info_list,
    )
