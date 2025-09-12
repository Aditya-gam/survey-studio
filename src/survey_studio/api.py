"""REST API functions for Survey Studio.

This module provides clean, reusable functions that can be used to build
REST API endpoints for the literature review assistant.
"""

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING, Any

from survey_studio.errors import (
    ConfigurationError,
    ExportError,
    ValidationError,
)
from survey_studio.export import (
    ExportMetadata,
    generate_filename,
    get_export_formats,
    to_html,
    to_markdown,
)
from survey_studio.logging import configure_logging, new_session_id, set_session_id
from survey_studio.orchestrator import run_survey_studio
from survey_studio.validation import validate_model, validate_num_papers, validate_topic

if TYPE_CHECKING:
    from typing import TypedDict

    class ReviewResults(TypedDict):
        session_id: str
        topic: str
        num_papers: int
        model: str
        status: str
        results: list[str]
        total_frames: int
        generated_at: str

    class ValidationResult(TypedDict, total=False):
        valid: bool
        message: str
        topic: str
        num_papers: int
        model: str
        error: str
        error_type: str

    class ExportContent(TypedDict):
        content: str
        filename: str
        mime_type: str
        format: str
        metadata: dict[str, Any]

    class ExportRequest(TypedDict, total=False):
        format_type: str

    class ExportRequestRequired(ExportRequest):
        topic: str
        results_frames: list[str]
        num_papers: int
        model: str
        session_id: str

    class HealthStatus(TypedDict, total=False):
        status: str
        providers: dict[str, Any]
        timestamp: str
        version: str
        error: str


def initialize_session() -> str:
    """Initialize a new session and return session ID.

    Returns:
        str: Session ID for tracking this review session
    """
    session_id = new_session_id()
    set_session_id(session_id)
    configure_logging()
    return session_id


def get_provider_status() -> dict[str, Any]:
    """Get current AI provider configuration status.

    Returns:
        Dict containing provider availability and configuration info
    """
    from survey_studio.llm_factory import get_provider_info

    provider_info = get_provider_info()

    return {
        "available_count": provider_info["available_count"],
        "best_provider": provider_info["best_provider"],
        "providers": [
            {
                "name": provider.provider.value,
                "model": provider.model,
                "priority": provider.priority,
                "free_tier_rpm": provider.free_tier_rpm,
                "free_tier_tpm": provider.free_tier_tpm,
            }
            for provider in provider_info.get("all_providers", [])
        ],
    }


def validate_review_request(topic: str, num_papers: int, model: str) -> "ValidationResult":
    """Validate a literature review request.

    Args:
        topic: Research topic
        num_papers: Number of papers to review
        model: AI model to use

    Returns:
        Dict containing validation result and any error messages

    Raises:
        ValidationError: If validation fails
        ConfigurationError: If no AI providers are configured
    """
    try:
        validate_topic(topic)
        validate_num_papers(num_papers)
        validate_model(model)
        return {
            "valid": True,
            "message": "Request is valid",
            "topic": topic,
            "num_papers": num_papers,
            "model": model,
        }
    except (ValidationError, ConfigurationError) as e:
        return {
            "valid": False,
            "error": str(e),
            "error_type": e.__class__.__name__,
            "topic": topic,
            "num_papers": num_papers,
            "model": model,
        }


async def run_literature_review(
    topic: str, num_papers: int, model: str, session_id: str | None = None
) -> "ReviewResults":
    """Run a literature review and return results.

    Args:
        topic: Research topic
        num_papers: Number of papers to review
        model: AI model to use (or "auto" for automatic selection)
        session_id: Optional session ID for tracking

    Returns:
        Dict containing review results and metadata

    Raises:
        ValidationError: If inputs are invalid
        ConfigurationError: If no AI providers are configured
        ExternalServiceError: If external services fail
        LLMError: If AI model fails
        SurveyStudioError: If review process fails
    """
    if not session_id:
        session_id = initialize_session()

    # Convert "auto" to None for the orchestrator
    model_for_orchestrator = None if model == "auto" else model

    # Run the review and collect results
    results_frames: list[str] = []
    current_phase = None

    async for frame in run_survey_studio(
        topic, num_papers=num_papers, model=model_for_orchestrator
    ):
        role, *_ = frame.split(":", 1)

        # Determine current phase
        if role == "search_agent":
            phase = "searching"
        elif role == "summarizer":
            phase = "summarizing"
        else:
            phase = current_phase or "searching"

        current_phase = phase

        # Store frame with metadata
        results_frames.append(frame)

    return {
        "session_id": session_id,
        "topic": topic,
        "num_papers": num_papers,
        "model": model,
        "status": "completed",
        "results": results_frames,
        "total_frames": len(results_frames),
        "generated_at": datetime.now().isoformat(),
    }


def generate_export(request: "ExportRequestRequired") -> "ExportContent":
    """Generate export content in specified format.

    Args:
        request: Export request containing:
            - topic: Research topic
            - results_frames: List of result frames from review
            - num_papers: Number of papers reviewed
            - model: AI model used
            - session_id: Session ID
            - format_type: Export format ("markdown" or "html")

    Returns:
        Dict containing export content and metadata

    Raises:
        ExportError: If export generation fails
        ValidationError: If inputs are invalid
    """
    format_type = request.get("format_type", "markdown")

    if not request["results_frames"]:
        raise ExportError("No results to export", format_type=format_type)

    # Create export metadata
    metadata = ExportMetadata(
        topic=request["topic"],
        generation_date=datetime.now().isoformat(),
        model_used=request["model"],
        session_id=request["session_id"],
        paper_count=request["num_papers"],
    )

    # Generate content based on format
    if format_type == "markdown":
        content = to_markdown(request["topic"], request["results_frames"], metadata)
        filename = generate_filename(
            request["topic"], get_export_formats()["markdown"]["extension"]
        )
        mime_type = get_export_formats()["markdown"]["mime_type"]
    elif format_type == "html":
        content = to_html(request["topic"], request["results_frames"], metadata)
        filename = generate_filename(request["topic"], get_export_formats()["html"]["extension"])
        mime_type = get_export_formats()["html"]["mime_type"]
    else:
        raise ExportError(f"Unsupported format: {format_type}", format_type=format_type)

    return {
        "content": content,
        "filename": filename,
        "mime_type": mime_type,
        "format": format_type,
        "metadata": {
            "topic": request["topic"],
            "num_papers": request["num_papers"],
            "model": request["model"],
            "session_id": request["session_id"],
            "generated_at": metadata.generation_date,
        },
    }


def get_available_models() -> dict[str, list[str]]:
    """Get list of available AI models by provider.

    Returns:
        Dict mapping provider names to lists of available models
    """
    from survey_studio.config import get_available_providers

    providers = get_available_providers()
    models: dict[str, list[str]] = {}

    for provider in providers:
        provider_name = provider.provider.value
        if provider_name not in models:
            models[provider_name] = []
        models[provider_name].append(provider.model)

    return models


def get_health_status() -> "HealthStatus":
    """Get overall health status of the service.

    Returns:
        Dict containing health status and component information
    """
    try:
        provider_status = get_provider_status()

        return {
            "status": "healthy" if provider_status["available_count"] > 0 else "degraded",
            "providers": provider_status,
            "timestamp": datetime.now().isoformat(),
            "version": "0.1.0",  # You might want to get this from package metadata
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "version": "0.1.0",
        }


def run_review_with_fallback(
    topic: str, num_papers: int, model: str, session_id: str | None = None
) -> "ReviewResults":
    """Run literature review with asyncio fallback handling.

    This is a synchronous wrapper around the async run_literature_review function.

    Args:
        topic: Research topic
        num_papers: Number of papers to review
        model: AI model to use
        session_id: Optional session ID

    Returns:
        Dict containing review results
    """
    try:
        return asyncio.run(run_literature_review(topic, num_papers, model, session_id))
    except RuntimeError:
        # Fallback for when an event loop is already running
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(run_literature_review(topic, num_papers, model, session_id))


def main() -> None:
    """Main entry point for the API server.

    This is a placeholder - you would implement your FastAPI app here.
    """
    print("Survey Studio API - Use these functions to build your REST endpoints")
    print("Available functions:")
    print("- initialize_session()")
    print("- get_provider_status()")
    print("- validate_review_request(topic, num_papers, model)")
    print("- run_literature_review(topic, num_papers, model, session_id)")
    print("- run_review_with_fallback(topic, num_papers, model, session_id)")
    print("- generate_export(request: ExportRequestRequired)")
    print("- get_available_models()")
    print("- get_health_status()")


if __name__ == "__main__":
    main()
