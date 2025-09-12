"""Export router for Survey Studio API.

Provides endpoints for exporting survey results to various formats.
"""

from fastapi import APIRouter

from survey_studio.core.errors import ValidationError
from survey_studio.schemas import ExportMetadata, ExportRequest, ExportResponse
from survey_studio.services.export_service import ExportService

router = APIRouter()


@router.post(
    "/export",
    response_model=ExportResponse,
    summary="Export survey results",
    description="Export survey results to various formats (Markdown, HTML)",
    tags=["export"],
)
async def export_results(request: ExportRequest) -> ExportResponse:
    """Export survey results to the specified format.

    Generates export content in the requested format (Markdown or HTML) from
    the provided survey results frames and metadata.

    Args:
        request: Export request containing results_frames, format_type, and metadata

    Returns:
        ExportResponse: Export content with filename and metadata

    Raises:
        ValidationError: If results_frames is empty or format_type is unsupported (handled as 400)
        ExportError: If export generation fails (handled as 500)
    """
    # Validate inputs
    if not request.results_frames:
        raise ValidationError("No results to export")

    # Validate format type
    supported_formats = ["markdown", "html"]
    if request.format_type not in supported_formats:
        supported_list = ", ".join(supported_formats)
        raise ValidationError(
            f"Unsupported format: {request.format_type}. Supported formats: {supported_list}"
        )

    # Generate export content
    export_content = ExportService.generate_export_content(request)

    # Convert metadata dict to ExportMetadata model
    metadata = ExportMetadata(
        topic=export_content["metadata"]["topic"],
        num_papers=export_content["metadata"]["num_papers"],
        model=export_content["metadata"]["model"],
        session_id=export_content["metadata"]["session_id"],
        generated_at=export_content["metadata"]["generated_at"],
    )

    return ExportResponse(
        content=export_content["content"],
        filename=export_content["filename"],
        mime_type=export_content["mime_type"],
        format=export_content["format"],
        metadata=metadata,
    )
