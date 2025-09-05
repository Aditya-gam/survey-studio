"""Streamlit frontend for the literature review assistant.

Imports the refactored orchestrator entrypoint and keeps UI concerns here.
Enhanced with comprehensive error handling, retry mechanisms, and notifications.
"""

import asyncio
from datetime import datetime
import logging

import streamlit as st

from .errors import (
    ConfigurationError,
    ExportError,
    ExternalServiceError,
    LLMError,
    SurveyStudioError,
    ValidationError,
)
from .export import (
    ExportMetadata,
    generate_filename,
    get_export_formats,
    to_html,
    to_markdown,
)
from .logging import configure_logging, new_session_id, set_session_id
from .orchestrator import run_survey_studio
from .ui.toasts import (
    handle_exception_with_toast,
    show_error_panel,
    show_info_toast,
    show_success_toast,
    show_warning_toast,
)
from .ui.validation_components import (
    render_advanced_options_sidebar,
    render_validation_helper,
    render_validation_status,
    validate_papers_input,
    validate_topic_input,
)


def configure_page() -> None:
    """Configure the Streamlit page settings."""
    st.set_page_config(
        page_title="Survey Studio - Literature Review Assistant",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            "Get Help": "https://github.com/survey-studio/survey-studio",
            "Report a bug": "https://github.com/survey-studio/survey-studio/issues",
            "About": """
            # Survey Studio

            A multi-agent literature review assistant using AutoGen and Streamlit.

            **Version:** 0.0.1
            """,
        },
    )


def render_sidebar() -> tuple[str, int, str, dict]:
    """Render the sidebar with configuration options and validation."""
    st.sidebar.title("📚 Survey Studio")
    st.sidebar.markdown("Configure your literature review")

    # Topic input with inline validation
    query = st.sidebar.text_input(
        "Research topic",
        placeholder="e.g., transformer architectures, quantum computing",
        help="Enter the research topic you want to review (3-200 characters)",
        key="topic_input",
    )

    # Show topic validation feedback
    if query:
        helper_text, state = validate_topic_input(query)
        render_validation_helper(helper_text, state)

    # Number of papers slider with validation
    n_papers = st.sidebar.slider(
        "Number of papers",
        min_value=1,
        max_value=10,
        value=5,
        help="Select how many papers to include in the review (1-10)",
        key="papers_slider",
    )

    # Show papers validation feedback
    helper_text, state = validate_papers_input(n_papers)
    render_validation_helper(helper_text, state)

    # Model selection
    model = st.sidebar.selectbox(
        "AI Model",
        options=["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
        index=0,
        help="Choose the AI model for the agents",
        key="model_select",
    )

    # Advanced options
    advanced_options = render_advanced_options_sidebar()

    return query, n_papers, model, advanced_options


def render_main_content(query: str, n_papers: int, model: str) -> None:
    """Render the main content area."""
    st.title("📚 Literature Review Assistant")
    st.markdown(
        """
        Welcome to Survey Studio! This tool uses AI agents to conduct
        comprehensive literature reviews by searching arXiv and generating
        structured summaries.

        **How it works:**
        1. 🔍 **Search Agent** finds relevant papers on arXiv
        2. 📝 **Summarizer Agent** creates a structured literature review
        3. 📋 You get a comprehensive overview of the research landscape
        """
    )

    if not query:
        st.info("👈 Please enter a research topic in the sidebar to get started.")
        return

    # Display current configuration
    with st.expander("Current Configuration", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Topic", query)
        with col2:
            st.metric("Papers", n_papers)
        with col3:
            st.metric("Model", model)


async def run_review_stream(query: str, n_papers: int, model: str) -> None:
    """Run the literature review and stream results."""
    chat_container = st.container()

    # Initialize results storage
    if "results_frames" not in st.session_state:
        st.session_state.results_frames = []

    # Clear previous results for new review
    st.session_state.results_frames = []

    with chat_container:
        st.subheader("🤖 Agent Conversation")

        async for frame in run_survey_studio(query, num_papers=n_papers, model=model):
            role, *rest = frame.split(":", 1)
            content = rest[0].strip() if rest else ""

            # Store frame for export functionality
            st.session_state.results_frames.append(frame)

            # Display agent messages with different styling
            if role == "search_agent":
                with st.chat_message("assistant", avatar="🔍"):
                    st.markdown(f"**Search Agent**: {content}")
            elif role == "summarizer":
                with st.chat_message("assistant", avatar="📝"):
                    st.markdown(f"**Summarizer**: {content}")
            else:
                with st.chat_message("assistant"):
                    st.markdown(f"**{role}**: {content}")


# Constants
OPERATION_LITERATURE_REVIEW = "literature review"
MIN_QUERY_LENGTH = 3
MAX_PAPERS_ALLOWED = 10


def main() -> None:
    """Main application entry point with enhanced error handling."""
    # Initialize session and logging
    _initialize_session()

    configure_page()
    show_error_panel()

    # Render sidebar and get configuration
    query, n_papers, model, advanced_options = render_sidebar()
    render_main_content(query, n_papers, model)

    # Validation status and button state management
    all_valid = render_validation_status(query, n_papers, advanced_options)
    button_disabled = not all_valid

    # Handle search button and execution
    if st.sidebar.button(
        "🚀 Start Review",
        type="primary",
        disabled=button_disabled,
        help="Start the literature review (requires valid inputs and API key)",
    ):
        _handle_review_execution(query, n_papers, model)


def _initialize_session() -> None:
    """Initialize session state and logging."""
    if "session_initialized" not in st.session_state:
        session_id = new_session_id()
        set_session_id(session_id)
        configure_logging()
        st.session_state.session_initialized = True
        st.session_state.session_id = session_id


def _handle_review_execution(query: str, n_papers: int, model: str) -> None:
    """Handle the literature review execution with error handling."""
    if not query:
        show_warning_toast("Please enter a research topic first!")
        return

    # Validate inputs
    try:
        validate_inputs(query, n_papers, model)
    except (ValidationError, ConfigurationError) as exc:
        handle_exception_with_toast(exc, "input validation")
        return

    # Run the literature review
    _execute_review(query, n_papers, model)

    # Handle download functionality
    _handle_download(query, n_papers, model)


def _execute_review(query: str, n_papers: int, model: str) -> None:
    """Execute the literature review with comprehensive error handling."""
    with st.spinner(f"Conducting literature review on '{query}'..."):
        try:
            show_info_toast(f"Starting literature review on '{query}'")

            # Run the main operation
            _run_review_with_fallback(query, n_papers, model)

            # Success feedback
            show_success_toast(
                "Literature review completed successfully!",
                f"Generated review for '{query}' with {n_papers} papers using {model}",
            )

        except ValidationError as ve:
            handle_exception_with_toast(ve, "input validation")

        except ConfigurationError as ce:
            handle_exception_with_toast(ce, "configuration")
            show_warning_toast(
                "Configuration issue detected",
                "Please check your API keys and model settings in the "
                "environment variables",
            )

        except ExternalServiceError as ese:
            handle_exception_with_toast(ese, "external service")
            show_warning_toast(
                f"Service temporarily unavailable: "
                f"{ese.context.get('service', 'Unknown')}",
                "Please try again in a few moments. If the problem persists, "
                "the service may be experiencing issues.",
            )

        except LLMError as le:
            handle_exception_with_toast(le, "AI model")
            show_warning_toast(
                "AI model encountered an issue",
                f"Model: {le.context.get('model', 'Unknown')}. This could be "
                "due to rate limits or service issues.",
            )

        except SurveyStudioError as se:
            handle_exception_with_toast(se, OPERATION_LITERATURE_REVIEW)

        except Exception as exc:
            handle_exception_with_toast(exc, OPERATION_LITERATURE_REVIEW)
            logging.getLogger(__name__).exception(
                "Unexpected error in main review process",
                extra={
                    "extra_fields": {
                        "query": query,
                        "model": model,
                        "n_papers": n_papers,
                    }
                },
            )


def _run_review_with_fallback(query: str, n_papers: int, model: str) -> None:
    """Run the review with asyncio fallback handling."""
    try:
        asyncio.run(run_review_stream(query, n_papers, model))
    except RuntimeError:
        # Fallback for when an event loop is already running
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_review_stream(query, n_papers, model))


def _handle_download(query: str, n_papers: int, model: str) -> None:
    """Handle enhanced export functionality with dual format support."""
    # Get stored results from session state
    results_frames = st.session_state.get("results_frames", [])

    if not results_frames:
        st.sidebar.info("📝 Complete a literature review first to enable downloads")
        return

    # Create export metadata
    metadata = ExportMetadata(
        topic=query,
        generation_date=datetime.now().isoformat(),
        model_used=model,
        session_id=st.session_state.get("session_id", "unknown"),
        paper_count=n_papers,
    )

    # Add help section for PDF export
    with st.sidebar.expander("📄 Export Help", expanded=False):
        st.markdown("""
        **Available Formats:**
        - **Markdown**: Source format with YAML metadata
        - **HTML**: Web-ready format with styling

        **For PDF Export:**
        1. Download HTML format
        2. Open in your browser
        3. Use browser's "Print" → "Save as PDF"
        4. Optimized for print with clean formatting
        """)

    # Export format selection
    st.sidebar.markdown("### 📥 Download Options")

    col1, col2 = st.sidebar.columns(2)

    # Markdown export
    with col1:
        if st.button(
            "📄 Markdown",
            help="Download as Markdown with YAML metadata",
            use_container_width=True,
        ):
            _export_format(query, results_frames, metadata, "markdown")

    # HTML export
    with col2:
        if st.button(
            "🌐 HTML", help="Download as HTML with styling", use_container_width=True
        ):
            _export_format(query, results_frames, metadata, "html")

    # Copy to clipboard options
    st.sidebar.markdown("### 📋 Copy Options")

    col3, col4 = st.sidebar.columns(2)

    with col3:
        if st.button(
            "📋 Copy MD", help="Copy Markdown to clipboard", use_container_width=True
        ):
            _copy_to_clipboard(query, results_frames, metadata, "markdown")

    with col4:
        if st.button(
            "📋 Copy HTML", help="Copy HTML to clipboard", use_container_width=True
        ):
            _copy_to_clipboard(query, results_frames, metadata, "html")


def _export_format(
    query: str, results_frames: list[str], metadata: ExportMetadata, format_type: str
) -> None:
    """Export content in specified format with error handling."""
    try:
        with st.spinner(f"Generating {format_type.upper()} export..."):
            progress_bar = st.progress(0)

            # Generate filename
            progress_bar.progress(20)
            filename = generate_filename(
                query, get_export_formats()[format_type]["extension"]
            )

            # Generate content based on format
            progress_bar.progress(50)
            if format_type == "markdown":
                content = to_markdown(query, results_frames, metadata)
            elif format_type == "html":
                content = to_html(query, results_frames, metadata)
            else:
                raise ExportError(
                    f"Unsupported format: {format_type}", format_type=format_type
                )

            progress_bar.progress(80)

            # Create download button
            mime_type = get_export_formats()[format_type]["mime_type"]

            st.download_button(
                label=f"💾 Save {filename}",
                data=content,
                file_name=filename,
                mime=mime_type,
                help=f"Click to download as {format_type.upper()}",
                use_container_width=True,
            )

            progress_bar.progress(100)
            progress_bar.empty()

            show_success_toast(
                f"{format_type.upper()} export ready",
                f"Click 'Save {filename}' to download your literature review",
            )

    except (ValidationError, ExportError) as e:
        handle_exception_with_toast(e, f"{format_type} export")

    except Exception as exc:
        handle_exception_with_toast(exc, f"{format_type} export preparation")


def _copy_to_clipboard(
    query: str, results_frames: list[str], metadata: ExportMetadata, format_type: str
) -> None:
    """Copy content to clipboard as fallback option."""
    try:
        with st.spinner(f"Preparing {format_type.upper()} for clipboard..."):
            # Generate content based on format
            if format_type == "markdown":
                content = to_markdown(query, results_frames, metadata)
            elif format_type == "html":
                content = to_html(query, results_frames, metadata)
            else:
                raise ExportError(
                    f"Unsupported format: {format_type}", format_type=format_type
                )

            # Display content in expandable text area for manual copying
            with st.expander(
                f"📋 {format_type.upper()} Content (Click to copy)", expanded=True
            ):
                st.text_area(
                    f"{format_type.upper()} Content",
                    value=content,
                    height=200,
                    help="Select all content and copy to clipboard",
                    key=f"copy_{format_type}_{metadata.session_id}",
                )

            show_info_toast(
                f"{format_type.upper()} ready to copy",
                "Select all text in the box above and copy to your clipboard",
            )

    except (ValidationError, ExportError) as e:
        handle_exception_with_toast(e, f"{format_type} clipboard preparation")

    except Exception as exc:
        handle_exception_with_toast(exc, f"{format_type} clipboard preparation")


def validate_inputs(query: str, n_papers: int, model: str) -> None:
    """Validate user inputs and raise ValidationError if invalid."""
    if not query or not query.strip():
        raise ValidationError("Research topic cannot be empty", field="query")

    if len(query.strip()) < MIN_QUERY_LENGTH:
        raise ValidationError(
            f"Research topic must be at least {MIN_QUERY_LENGTH} characters long",
            field="query",
        )

    if n_papers < 1 or n_papers > MAX_PAPERS_ALLOWED:
        raise ValidationError(
            f"Number of papers must be between 1 and {MAX_PAPERS_ALLOWED}",
            field="n_papers",
        )

    if model not in ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"]:
        raise ValidationError(f"Invalid model selected: {model}", field="model")

    # Check for API key configuration (basic check)
    import os

    if not os.getenv("OPENAI_API_KEY"):
        raise ConfigurationError(
            "OpenAI API key not configured",
            context={"missing_env_var": "OPENAI_API_KEY"},
        )


if __name__ == "__main__":
    main()
