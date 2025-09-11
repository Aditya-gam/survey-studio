"""Streamlit frontend for the literature review assistant.

Imports the refactored orchestrator entrypoint and keeps UI concerns here.
Enhanced with comprehensive error handling, retry mechanisms, and notifications.
"""

import asyncio
from datetime import datetime
from importlib import metadata
import logging
import os
import subprocess
from typing import Any

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
from .ui.components import (
    empty_state as render_empty_state,
    footer as render_footer,
    progress_steps,
    sidebar_about,
    sidebar_troubleshooting,
)
from .ui.navbar import (
    get_navbar_form_values,
    manage_loading_states,
    render_navbar,
    set_navbar_form_values,
    validate_navbar_inputs,
)
from .ui.toasts import (
    handle_exception_with_toast,
    show_info_toast,
    show_success_toast,
    show_warning_toast,
)
from .ui.validation_components import (
    render_advanced_options_sidebar,
)


def configure_page() -> None:
    """Configure the Streamlit page settings."""
    st.set_page_config(
        page_title="Survey Studio - Literature Review Assistant",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="collapsed",  # Collapsed since we use navbar now
        menu_items={
            "Get Help": "https://github.com/Aditya-gam/survey-studio",
            "Report a bug": "https://github.com/Aditya-gam/survey-studio/issues",
            "About": """
            # Survey Studio

            A multi-agent literature review assistant using AutoGen and Streamlit.

            **Version:** 0.0.1
            """,
        },
    )

    # Add custom CSS for navbar integration
    st.markdown(
        """
        <style>
        /* Hide default Streamlit header and adjust main content area */
        .stApp > header {
            height: 0px;
        }

        .main .block-container {
            padding-top: 80px;  /* Account for fixed navbar */
            max-width: 100%;
        }

        /* Ensure sidebar doesn't overlap with navbar */
        .sidebar .sidebar-content {
            margin-top: 64px;
        }

        /* Fix for mobile responsiveness */
        @media (max-width: 768px) {
            .main .block-container {
                padding-top: 70px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> dict[str, Any]:
    """Render the simplified sidebar with advanced options only."""
    st.sidebar.title("⚙️ Advanced Options")
    st.sidebar.caption("Additional configuration and information")

    # AI Provider and Model selection info
    from .llm_factory import get_provider_info

    provider_info = get_provider_info()

    if provider_info["available_count"] > 0:
        st.sidebar.success(f"✅ {provider_info['available_count']} AI provider(s) available")
        if provider_info["best_provider"]:
            st.sidebar.info(f"🎯 Using: {provider_info['best_provider'].title()}")
    else:
        st.sidebar.error("❌ No AI providers configured")

    # Advanced options
    advanced_options = render_advanced_options_sidebar()

    # Export functionality (moved to sidebar)
    _handle_download_sidebar()

    # Informational sections
    sidebar_about()
    sidebar_troubleshooting()

    return advanced_options


def render_main_content(query: str, n_papers: int, model: str) -> None:
    """Render the main content area with guidance."""
    # Main content now starts below the fixed navbar
    if not query:
        render_empty_state()
        return

    # Show a clean, minimal summary
    st.markdown("### Ready to Start")

    # Create a clean summary card
    col1, col2, col3 = st.columns(3)

    with col1:
        max_topic_display_length = 30
        st.metric(
            "Research Topic",
            query[:max_topic_display_length] + "..."
            if len(query) > max_topic_display_length
            else query,
        )

    with col2:
        st.metric("Papers to Review", n_papers)

    with col3:
        st.metric("AI Model", model.title())

    st.markdown("---")
    st.markdown("Use the **Search** button in the navbar to begin your literature review.")


async def run_review_stream(query: str, n_papers: int, model: str) -> None:
    """Run the literature review and stream results."""
    steps = ["Searching", "Summarizing"]
    chat_container = st.container()
    step_placeholder = st.empty()

    # Initialize results storage with proper typing
    if "results_frames" not in st.session_state:
        st.session_state.results_frames = []

    # Create a properly typed list
    results_frames: list[str] = []

    # Clear previous results for new review
    st.session_state.results_frames = []

    current_phase = None

    with chat_container:
        st.subheader("🤖 Agent Conversation")

        # Convert "auto" to None for the orchestrator
        model_for_orchestrator = None if model == "auto" else model
        async for frame in run_survey_studio(
            query, num_papers=n_papers, model=model_for_orchestrator
        ):
            role, *rest = frame.split(":", 1)
            content = rest[0].strip() if rest else ""

            # Update progress step subtly
            if role == "search_agent":
                phase = "Searching"
            elif role == "summarizer":
                phase = "Summarizing"
            else:
                phase = current_phase or "Searching"

            if phase != current_phase:
                if current_phase is not None:
                    st.divider()
                current_phase = phase
            with step_placeholder.container():
                progress_steps(current_step=current_phase or "Searching", steps=steps)

            # Store frame for export functionality
            results_frames.append(frame)
            st.session_state.results_frames = results_frames

            # Display agent messages with different styling
            if role == "search_agent":
                with st.chat_message("assistant", avatar="🔎"):
                    st.markdown("**Search Agent**")
                    st.write(content)
            elif role == "summarizer":
                with st.chat_message("assistant", avatar="🧠"):
                    st.markdown("**Summarizer**")
                    st.write(content)
            else:
                with st.chat_message("assistant"):
                    st.markdown(f"**{role}**")
                    st.write(content)

    # Mark completion for CTA visibility
    st.session_state.run_completed = True


# Constants
OPERATION_LITERATURE_REVIEW = "literature review"
MIN_QUERY_LENGTH = 3
MAX_PAPERS_ALLOWED = 10


def main() -> None:
    """Main application entry point with enhanced error handling."""
    # Initialize session and logging
    _initialize_session()

    configure_page()

    # Define search handler function
    def handle_navbar_search() -> None:
        """Handle search button click from navbar."""
        query, n_papers, model = get_navbar_form_values()

        # Validate inputs using navbar validation
        is_valid, errors = validate_navbar_inputs()

        if not is_valid:
            for error in errors:
                show_warning_toast(error)
            return

        # Set loading state
        manage_loading_states(True)

        try:
            _handle_review_execution(query, n_papers, model)
        finally:
            manage_loading_states(False)

    # Render navbar with search handler
    render_navbar(on_search_click=handle_navbar_search)

    # Get current form values from navbar
    query, n_papers, model = get_navbar_form_values()

    # Render simplified sidebar
    render_sidebar()

    # Render main content
    render_main_content(query, n_papers, model)

    # Post-completion CTA in main area
    if st.session_state.get("run_completed"):
        st.success("Review complete.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Run Again", type="primary", use_container_width=True):
                # Reset form values
                set_navbar_form_values("", 5, "auto")
                st.session_state.results_frames = []
                st.session_state.run_completed = False
                st.rerun()
        with col2:
            if st.button("📋 New Topic", type="secondary", use_container_width=True):
                # Clear only the topic
                set_navbar_form_values("", n_papers, model)
                st.session_state.results_frames = []
                st.session_state.run_completed = False
                st.rerun()

    # Footer with version and commit SHA
    try:
        version = _get_app_version()
    except Exception:
        version = "unknown"
    sha_short = _get_short_commit_sha()
    render_footer(app_version=version, commit_sha_short=sha_short)


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


def _get_app_version() -> str:
    """Return the application version from distribution or pyproject.toml."""
    # Try installed distribution metadata first
    try:
        return metadata.version("survey-studio")
    except Exception:
        pass

    # Fallback: parse pyproject.toml in repo
    try:
        import tomllib  # Python 3.11+

        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        pyproject_path = os.path.join(repo_root, "pyproject.toml")
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
        return data.get("project", {}).get("version", "unknown")
    except Exception:
        return "unknown"


def _get_short_commit_sha() -> str:
    """Return the short commit SHA if available, else empty string."""
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL
            )
            .decode()
            .strip()
        )
    except Exception:
        return os.getenv("GIT_COMMIT_SHA_SHORT", "")


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
                "Please check your API keys and model settings in the " + "environment variables",
            )

        except ExternalServiceError as ese:
            handle_exception_with_toast(ese, "external service")
            show_warning_toast(
                "Service temporarily unavailable: " + f"{ese.context.get('service', 'Unknown')}",
                "Please try again in a few moments. If the problem persists, "
                + "the service may be experiencing issues.",
            )

        except LLMError as le:
            handle_exception_with_toast(le, "AI model")
            show_warning_toast(
                "AI model encountered an issue",
                f"Model: {le.context.get('model', 'Unknown')}. This could be "
                + "due to rate limits or service issues.",
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


def _handle_download_sidebar() -> None:
    """Handle enhanced export functionality in the sidebar."""
    # Get stored results from session state
    results_frames = st.session_state.get("results_frames", [])

    if not results_frames:
        return

    # Get current form values for metadata
    query, n_papers, model = get_navbar_form_values()
    _handle_download(query, n_papers, model)


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
        if st.button("🌐 HTML", help="Download as HTML with styling", use_container_width=True):
            _export_format(query, results_frames, metadata, "html")

    # Copy to clipboard options
    st.sidebar.markdown("### 📋 Copy Options")

    col3, col4 = st.sidebar.columns(2)

    with col3:
        if st.button("📋 Copy MD", help="Copy Markdown to clipboard", use_container_width=True):
            _copy_to_clipboard(query, results_frames, metadata, "markdown")

    with col4:
        if st.button("📋 Copy HTML", help="Copy HTML to clipboard", use_container_width=True):
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
            filename = generate_filename(query, get_export_formats()[format_type]["extension"])

            # Generate content based on format
            progress_bar.progress(50)
            if format_type == "markdown":
                content = to_markdown(query, results_frames, metadata)
            elif format_type == "html":
                content = to_html(query, results_frames, metadata)
            else:
                raise ExportError(f"Unsupported format: {format_type}", format_type=format_type)

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
                raise ExportError(f"Unsupported format: {format_type}", format_type=format_type)

            # Display content in expandable text area for manual copying
            with st.expander(f"📋 {format_type.upper()} Content (Click to copy)", expanded=True):
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


def validate_inputs(query: str, n_papers: int, model: str | None) -> None:
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

    if model and model not in ["auto", "gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"]:
        raise ValidationError(f"Invalid model selected: {model}", field="model")

    # Check for AI provider configuration
    from .config import get_best_available_provider

    if not get_best_available_provider():
        raise ConfigurationError(
            (
                "No AI providers are available. Please configure at least one API key "
                "(TOGETHER_AI_API_KEY, GEMINI_API_KEY, PERPLEXITY_API_KEY, or OPENAI_API_KEY) "
                "in .env file, environment variables, or Streamlit secrets."
            ),
            context={"missing_config": "ai_providers"},
        )


if __name__ == "__main__":
    main()
