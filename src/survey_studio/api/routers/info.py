"""Info router for Survey Studio API.

Provides basic service information including name, version, and documentation URL.
"""

from fastapi import APIRouter

from survey_studio.schemas import InfoResponse

router = APIRouter()


@router.get(
    "/",
    response_model=InfoResponse,
    summary="Get service information",
    description="Returns basic information about the Survey Studio service.",
    tags=["info"],
)
async def get_info() -> InfoResponse:
    """Get basic service information.

    Returns:
        InfoResponse: Service name, version, and documentation URL
    """
    return InfoResponse(
        name="survey-studio",
        version="0.1.0",
        docs="/docs",
    )
