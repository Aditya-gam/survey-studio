"""Streamlit frontend for the literature review assistant.

Imports the refactored orchestrator entrypoint and keeps UI concerns here.
Enhanced with comprehensive error handling, retry mechanisms, and notifications.
"""

import asyncio
import logging

import streamlit as st

from .errors import (
    ConfigurationError,
    ExternalServiceError,
    LLMError,
    SurveyStudioError,
    ValidationError,
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

    with chat_container:
        st.subheader("🤖 Agent Conversation")

        async for frame in run_survey_studio(query, num_papers=n_papers, model=model):
            role, *rest = frame.split(":", 1)
            content = rest[0].strip() if rest else ""

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
    """Handle download functionality."""
    if st.sidebar.button(
        "📥 Download Results", help="Download the literature review results"
    ):
        try:
            # Placeholder for future enhancement
            download_data = (
                f"# Literature Review: {query}\n\n"
                f"Generated on: {st.session_state.get('session_id', 'unknown')}\n"
                f"Model: {model}\nPapers: {n_papers}\n\n[Results would be here...]"
            )

            st.sidebar.download_button(
                label="📥 Download Markdown",
                data=download_data,
                file_name=f"literature_review_{query.replace(' ', '_')}.md",
                mime="text/markdown",
            )

            show_success_toast(
                "Download prepared", "Click the download button to save your results"
            )

        except Exception as exc:
            handle_exception_with_toast(exc, "download preparation")


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
