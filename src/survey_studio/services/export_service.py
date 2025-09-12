"""Export service for Survey Studio API.

This module provides the ExportService class that wraps export
functions from the API module with proper error handling and type hints.
"""

from typing import TYPE_CHECKING

from survey_studio.api.functions import generate_export

if TYPE_CHECKING:
    from survey_studio.api.functions import ExportContent, ExportRequestRequired
    from survey_studio.schemas import ExportRequest


class ExportService:
    """Service class for export operations.

    Provides static methods that wrap export functions from the API module
    with consistent error handling and return types.
    """

    @staticmethod
    def generate_export_content(request: "ExportRequest") -> "ExportContent":
        """Generate export content in the specified format.

        Args:
            request: Export request containing topic, results_frames, num_papers,
                    model, session_id, and format_type

        Returns:
            ExportContent: Dict containing export content and metadata

        Raises:
            ExportError: If export generation fails
            ValidationError: If inputs are invalid
        """
        api_request: ExportRequestRequired = {
            "topic": request.topic,
            "results_frames": request.results_frames,
            "num_papers": request.num_papers,
            "model": request.model,
            "session_id": request.session_id,
            "format_type": request.format_type,
        }
        return generate_export(api_request)
