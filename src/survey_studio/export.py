"""Export utilities for Survey Studio literature reviews.

Provides comprehensive export functionality including Markdown and HTML formats
with metadata, sanitization, and error handling for robust download operations.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import html
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable

from markdown_it import MarkdownIt

from .errors import ExportError, ValidationError
from .retry import retry_export_operations

# Constants
MAX_FILENAME_LENGTH = 100
SAFE_FILENAME_PATTERN = r"[^a-zA-Z0-9_\-\.]"
HTML_DOCTYPE = "<!DOCTYPE html>"
MIN_TOPIC_LENGTH = 20  # Minimum length to keep meaningful text
MIN_TRUNCATED_LENGTH = 5  # Minimum meaningful topic length


@dataclass(frozen=True)
class Paper:
    """Represents a research paper with metadata."""

    title: str
    authors: list[str]
    published: str
    summary: str
    pdf_url: str


@dataclass(frozen=True)
class ExportMetadata:
    """Metadata for literature review export."""

    topic: str
    generation_date: str
    model_used: str
    session_id: str
    paper_count: int
    version: str = "0.1.0"


def _sanitize_topic_for_filename(topic: str) -> str:
    """Sanitize topic string for use in filename."""
    if not topic or not topic.strip():
        return "untitled"

    # Replace spaces with underscores and remove/replace unsafe characters
    sanitized = re.sub(SAFE_FILENAME_PATTERN, "_", topic.strip().lower())

    # Remove multiple consecutive underscores
    sanitized = re.sub(r"_{2,}", "_", sanitized)

    # Remove leading/trailing underscores
    sanitized = sanitized.strip("_")

    # Limit length while preserving readability
    if (
        len(sanitized) > MAX_FILENAME_LENGTH - 30
    ):  # Reserve space for timestamp and extension
        sanitized = sanitized[: MAX_FILENAME_LENGTH - 30]
        # Don't cut in the middle of a word - find last underscore
        last_underscore = sanitized.rfind("_")
        if last_underscore > MIN_TOPIC_LENGTH:  # Keep at least some meaningful text
            sanitized = sanitized[:last_underscore]

    return sanitized or "untitled"


def _validate_export_inputs(topic: str, content_frames: Iterable[str]) -> None:
    """Validate inputs for export functions."""
    if not topic:
        raise ValidationError("Topic must be a non-empty string", field="topic")

    # Check if content_frames is iterable by trying to iterate it
    try:
        iter(content_frames)
    except TypeError as err:
        raise ValidationError(
            "Content frames must be iterable", field="content_frames"
        ) from err


def _create_yaml_frontmatter(metadata: ExportMetadata) -> str:
    """Create YAML frontmatter for markdown export."""
    return f"""---
title: "Literature Review: {metadata.topic}"
topic: "{metadata.topic}"
generated_date: "{metadata.generation_date}"
model_used: "{metadata.model_used}"
session_id: "{metadata.session_id}"
paper_count: {metadata.paper_count}
version: "{metadata.version}"
export_format: "markdown"
---

"""


@retry_export_operations
def generate_filename(
    topic: str, file_format: str, timestamp: datetime | None = None
) -> str:
    """Generate safe filename for export with timestamp.

    Args:
        topic: The research topic
        file_format: File extension (md, html)
        timestamp: Optional timestamp, defaults to current time

    Returns:
        Sanitized filename following pattern:
        survey_studio_{topic_snake}_{YYYYMMDD_HHMM}.{ext}

    Raises:
        ValidationError: If inputs are invalid
        ExportError: If filename generation fails
    """
    try:
        if not topic:
            raise ValidationError("Topic must be a non-empty string", field="topic")

        if not file_format:
            raise ValidationError(
                "File format must be a non-empty string", field="file_format"
            )

        if file_format not in ["md", "html"]:
            raise ValidationError(
                "File format must be 'md' or 'html'", field="file_format"
            )

        # Use provided timestamp or current time
        if timestamp is None:
            timestamp = datetime.now()

        # Sanitize topic for filename
        sanitized_topic = _sanitize_topic_for_filename(topic)

        # Format timestamp
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M")

        # Generate filename
        filename = f"survey_studio_{sanitized_topic}_{timestamp_str}.{file_format}"

        # Final length check
        if len(filename) > MAX_FILENAME_LENGTH:
            # Truncate topic part while preserving timestamp and format
            available_length = MAX_FILENAME_LENGTH - len(
                f"survey_studio__{timestamp_str}.{file_format}"
            )

            # Minimum meaningful topic length
            if available_length > MIN_TRUNCATED_LENGTH:
                sanitized_topic = sanitized_topic[:available_length]
                filename = (
                    f"survey_studio_{sanitized_topic}_{timestamp_str}.{file_format}"
                )
            else:
                # Fallback if topic is too long
                filename = f"survey_studio_{timestamp_str}.{file_format}"

        return filename

    except (ValidationError, ExportError):
        raise
    except Exception as e:
        raise ExportError(
            f"Failed to generate filename: {str(e)}",
            format_type=file_format,
            context={"topic": topic, "format": file_format},
        ) from e


@retry_export_operations
def to_markdown(
    topic: str,
    generated_text_frames: Iterable[str],
    metadata: ExportMetadata | None = None,
) -> str:
    """Return a Markdown string with comprehensive metadata and content.

    Enhanced version that includes YAML frontmatter with metadata and preserves
    all agent-generated content with proper structure.

    Args:
        topic: The research topic
        generated_text_frames: Iterable of content frames from agents
        metadata: Optional export metadata, creates minimal if not provided

    Returns:
        Complete markdown document with YAML frontmatter and content

    Raises:
        ValidationError: If inputs are invalid
        ExportError: If markdown generation fails
    """
    try:
        _validate_export_inputs(topic, generated_text_frames)

        # Convert frames to list for processing
        content_list = list(generated_text_frames)

        # Create metadata if not provided
        if metadata is None:
            metadata = ExportMetadata(
                topic=topic,
                generation_date=datetime.now().isoformat(),
                model_used="unknown",
                session_id="unknown",
                paper_count=0,
            )

        # Create YAML frontmatter
        frontmatter = _create_yaml_frontmatter(metadata)

        # Create main header
        header = f"# Literature Review: {topic}\n\n"

        # Add metadata section
        metadata_section = f"""## Review Information

- **Topic**: {metadata.topic}
- **Generated**: {metadata.generation_date}
- **Model**: {metadata.model_used}
- **Papers Analyzed**: {metadata.paper_count}
- **Session ID**: {metadata.session_id}

---

"""

        # Combine content frames
        body = "\n".join(content_list) if content_list else "*No content generated*"

        # Ensure final newline
        if not body.endswith("\n"):
            body += "\n"

        return frontmatter + header + metadata_section + body

    except (ValidationError, ExportError):
        raise
    except Exception as e:
        raise ExportError(
            f"Failed to generate markdown: {str(e)}",
            format_type="markdown",
            context={
                "topic": topic,
                "content_frames_count": len(list(generated_text_frames)),
            },
        ) from e


def _get_html_css() -> str:
    """Return minimal inline CSS for HTML export."""
    return """
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
                         'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
            color: #333;
            background: #fff;
        }

        h1, h2, h3, h4, h5, h6 {
            color: #2c3e50;
            margin-top: 2rem;
            margin-bottom: 1rem;
        }

        h1 {
            border-bottom: 3px solid #3498db;
            padding-bottom: 0.5rem;
        }

        h2 {
            border-bottom: 1px solid #bdc3c7;
            padding-bottom: 0.3rem;
        }

        p {
            margin-bottom: 1rem;
            text-align: justify;
        }

        ul, ol {
            margin-bottom: 1rem;
            padding-left: 2rem;
        }

        li {
            margin-bottom: 0.5rem;
        }

        blockquote {
            border-left: 4px solid #3498db;
            padding-left: 1rem;
            margin: 1rem 0;
            color: #7f8c8d;
            font-style: italic;
        }

        code {
            background: #f8f9fa;
            padding: 0.2rem 0.4rem;
            border-radius: 3px;
            font-family: 'SF Mono', Consolas, 'Liberation Mono', monospace;
            font-size: 0.85em;
        }

        pre {
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 5px;
            overflow-x: auto;
            margin: 1rem 0;
        }

        pre code {
            background: none;
            padding: 0;
        }

        .metadata {
            background: #ecf0f1;
            padding: 1rem;
            border-radius: 5px;
            margin: 1rem 0;
            font-size: 0.9em;
        }

        .metadata ul {
            margin: 0;
            list-style: none;
            padding: 0;
        }

        .metadata li {
            margin-bottom: 0.3rem;
        }

        .metadata strong {
            color: #2c3e50;
        }

        hr {
            border: none;
            height: 1px;
            background: #bdc3c7;
            margin: 2rem 0;
        }

        @media print {
            body {
                max-width: none;
                margin: 0;
                padding: 1rem;
            }

            .metadata {
                background: #f8f9fa;
                border: 1px solid #ddd;
            }
        }

        @media (max-width: 768px) {
            body {
                padding: 1rem;
            }

            h1 {
                font-size: 1.5rem;
            }

            h2 {
                font-size: 1.3rem;
            }
        }
    </style>
"""


@retry_export_operations
def to_html(
    topic: str,
    generated_text_frames: Iterable[str],
    metadata: ExportMetadata | None = None,
) -> str:
    """Convert markdown content to HTML with minimal inline CSS.

    Args:
        topic: The research topic
        generated_text_frames: Iterable of content frames from agents
        metadata: Optional export metadata, creates minimal if not provided

    Returns:
        Complete HTML document with CSS styling and metadata

    Raises:
        ValidationError: If inputs are invalid
        ExportError: If HTML generation fails
    """
    # Initialize content_list to avoid unbound variable issues
    content_list: list[str] = []

    try:
        _validate_export_inputs(topic, generated_text_frames)

        # Convert frames to list for processing
        content_list = list(generated_text_frames)

        # Create metadata if not provided
        if metadata is None:
            metadata = ExportMetadata(
                topic=topic,
                generation_date=datetime.now().isoformat(),
                model_used="unknown",
                session_id="unknown",
                paper_count=0,
            )

        # First generate markdown content (without frontmatter for HTML)
        markdown_content = f"# Literature Review: {topic}\n\n"

        # Add metadata section with HTML-friendly structure
        metadata_section = f"""## Review Information

- **Topic**: {metadata.topic}
- **Generated**: {metadata.generation_date}
- **Model**: {metadata.model_used}
- **Papers Analyzed**: {metadata.paper_count}
- **Session ID**: {metadata.session_id}

---

"""

        # Combine content
        body = "\n".join(content_list) if content_list else "*No content generated*"
        full_markdown = markdown_content + metadata_section + body

        # Convert markdown to HTML
        md = MarkdownIt()
        html_body = md.render(full_markdown)

        # Escape topic for HTML title
        escaped_topic = html.escape(topic)

        # Create complete HTML document and return directly
        return f"""{HTML_DOCTYPE}
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="generator" content="Survey Studio v{metadata.version}">
    <meta name="topic" content="{escaped_topic}">
    <meta name="generated-date" content="{metadata.generation_date}">
    <meta name="model-used" content="{metadata.model_used}">
    <meta name="session-id" content="{metadata.session_id}">
    <meta name="paper-count" content="{metadata.paper_count}">
    <title>Literature Review: {escaped_topic}</title>
    {_get_html_css()}
</head>
<body>
    {html_body}

    <footer style="margin-top: 3rem; padding-top: 1rem; border-top: 1px solid #bdc3c7;
                   font-size: 0.8em; color: #7f8c8d; text-align: center;">
        Generated by Survey Studio v{metadata.version} on {metadata.generation_date}
    </footer>
</body>
</html>"""

    except (ValidationError, ExportError):
        raise
    except Exception as e:
        raise ExportError(
            f"Failed to generate HTML: {str(e)}",
            format_type="html",
            context={"topic": topic, "content_frames_count": len(content_list)},
        ) from e


def get_export_formats() -> dict[str, dict[str, Any]]:
    """Get available export formats and their configurations."""
    return {
        "markdown": {
            "extension": "md",
            "mime_type": "text/markdown",
            "function": to_markdown,
            "description": "Markdown format with YAML frontmatter",
        },
        "html": {
            "extension": "html",
            "mime_type": "text/html",
            "function": to_html,
            "description": "HTML format with inline CSS styling",
        },
    }
