"""Health check router for Survey Studio API.

Provides health status information including provider status and service health.
"""

from fastapi import APIRouter

from survey_studio.schemas import HealthResponse, ProviderInfo, ProviderStatusData

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Get service health status",
    description="Returns the current health status of the Survey Studio service.",
    tags=["health"],
)
async def get_health() -> HealthResponse:
    """Get service health status.

    Calls the existing get_health_status function and converts the result
    to a proper Pydantic response model.

    Returns:
        HealthResponse: Current service health status
    """
    # Import here to avoid circular imports
    from survey_studio.api import get_health_status  # noqa: PLC0415

    health_data = get_health_status()

    # Convert provider status to Pydantic model
    providers_data = health_data.get("providers", {})
    provider_info_list = [
        ProviderInfo(
            name=provider["name"],
            model=provider["model"],
            priority=provider["priority"],
            free_tier_rpm=provider["free_tier_rpm"],
            free_tier_tpm=provider["free_tier_tpm"],
        )
        for provider in providers_data.get("providers", [])
    ]

    provider_status = ProviderStatusData(
        available_count=providers_data.get("available_count", 0),
        best_provider=providers_data.get("best_provider", ""),
        providers=provider_info_list,
    )

    return HealthResponse(
        status=health_data.get("status", "unknown"),
        providers=provider_status,
        timestamp=health_data.get("timestamp", ""),
        version=health_data.get("version", "0.1.0"),
        error=health_data.get("error"),
    )
