"""Pydantic models for Survey Studio API responses.

This module defines all the response schemas used by the FastAPI endpoints,
providing proper type validation and OpenAPI documentation generation.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# Constants for field descriptions
RESEARCH_TOPIC_DESC = "Research topic"
NUM_PAPERS_DESC = "Number of papers reviewed"
AI_MODEL_DESC = "AI model used"
SESSION_ID_DESC = "Session identifier"


class InfoResponse(BaseModel):
    """Response model for service information endpoint."""

    name: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    docs: str = Field(..., description="API documentation URL")


class ProviderInfo(BaseModel):
    """Model for individual AI provider information."""

    name: str = Field(..., description="Provider name")
    model: str = Field(..., description="Model identifier")
    priority: int = Field(..., description="Provider priority")
    free_tier_rpm: int = Field(..., description="Free tier requests per minute")
    free_tier_tpm: int = Field(..., description="Free tier tokens per minute")


class ProviderStatusData(BaseModel):
    """Model for provider status information."""

    available_count: int = Field(..., description="Number of available providers")
    best_provider: str | None = Field(None, description="Best available provider")
    providers: list[ProviderInfo] = Field(
        default_factory=lambda: list[ProviderInfo](), description="List of configured providers"
    )


class ProviderResponse(BaseModel):
    """Response model for provider status endpoint."""

    available_count: int = Field(..., description="Number of available providers")
    best_provider: str | None = Field(None, description="Best available provider")
    providers: list[ProviderInfo] = Field(
        default_factory=lambda: list[ProviderInfo](), description="List of configured providers"
    )


class HealthResponse(BaseModel):
    """Response model for health status endpoint."""

    status: str = Field(..., description="Overall health status")
    providers: ProviderStatusData = Field(..., description="Provider status information")
    timestamp: str = Field(..., description="Timestamp of health check")
    version: str = Field(..., description="Service version")
    error: str | None = Field(None, description="Error message if unhealthy")


class ModelsResponse(BaseModel):
    """Response model for available models endpoint."""

    models: dict[str, list[str]] = Field(..., description="Available models grouped by provider")


class ValidateResponse(BaseModel):
    """Response model for successful validation."""

    status: str = Field(..., description="Validation status")
    results: dict[str, Any] = Field(..., description="Validation results")


class ReviewResponse(BaseModel):
    """Response model for successful review."""

    status: str = Field(..., description="Review status")
    results: list[str] = Field(..., description="Review result frames")


# Additional models for future endpoints


class ValidationResult(BaseModel):
    """Model for validation results."""

    valid: bool = Field(..., description="Whether the validation passed")
    message: str = Field(..., description="Validation message")
    topic: str | None = Field(None, description="Validated topic")
    num_papers: int | None = Field(None, description="Validated number of papers")
    model: str | None = Field(None, description="Validated model")
    error: str | None = Field(None, description="Error message if validation failed")
    error_type: str | None = Field(None, description="Type of validation error")


class ExportMetadata(BaseModel):
    """Model for export metadata."""

    topic: str = Field(..., description=RESEARCH_TOPIC_DESC)
    num_papers: int = Field(..., description=NUM_PAPERS_DESC)
    model: str = Field(..., description=AI_MODEL_DESC)
    session_id: str = Field(..., description=SESSION_ID_DESC)
    generated_at: str = Field(..., description="Export generation timestamp")


class ExportResponse(BaseModel):
    """Response model for export generation."""

    content: str = Field(..., description="Generated export content")
    filename: str = Field(..., description="Suggested filename")
    mime_type: str = Field(..., description="MIME type of the content")
    format: str = Field(..., description="Export format")
    metadata: ExportMetadata = Field(..., description="Export metadata")


class ReviewResults(BaseModel):
    """Model for literature review results."""

    session_id: str = Field(..., description="Session identifier")
    topic: str = Field(..., description="Research topic")
    num_papers: int = Field(..., description="Number of papers reviewed")
    model: str = Field(..., description="AI model used")
    status: str = Field(..., description="Review status")
    results: list[str] = Field(..., description="Review result frames")
    total_frames: int = Field(..., description="Total number of result frames")
    generated_at: str = Field(..., description="Results generation timestamp")


# Request models for future endpoints


class ReviewRequest(BaseModel):
    """Request model for literature review."""

    topic: str = Field(..., min_length=1, max_length=500, description="Research topic")
    num_papers: int = Field(..., ge=1, le=50, description="Number of papers to review")
    model: str = Field(..., description="AI model to use or 'auto' for automatic selection")


class ReviewValidateRequest(BaseModel):
    """Request model for review validation."""

    topic: str = Field(..., min_length=1, max_length=500, description="Research topic")
    num_papers: int = Field(..., ge=1, le=50, description="Number of papers to review")
    model: str = Field(..., description="AI model to use or 'auto' for automatic selection")


class ExportRequest(BaseModel):
    """Request model for export generation."""

    topic: str = Field(..., description="Research topic")
    results_frames: list[str] = Field(..., description="Review result frames")
    num_papers: int = Field(..., description="Number of papers reviewed")
    model: str = Field(..., description="AI model used")
    session_id: str = Field(..., description="Session identifier")
    format_type: str = Field(default="markdown", description="Export format")


# Error response models


class ErrorResponse(BaseModel):
    """Standard error response model."""

    error: str = Field(..., description="Error message")
    error_type: str = Field(..., description="Error type/class")
    error_id: str | None = Field(None, description="Unique error identifier")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    context: dict[str, Any] | None = Field(None, description="Additional error context")


class ValidationErrorResponse(ErrorResponse):
    """Error response model for validation errors."""

    field: str | None = Field(None, description="Field that failed validation")


class ConfigurationErrorResponse(ErrorResponse):
    """Error response model for configuration errors."""


class ExternalServiceErrorResponse(ErrorResponse):
    """Error response model for external service errors."""

    service: str | None = Field(None, description="External service that failed")
