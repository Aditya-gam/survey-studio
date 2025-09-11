"""Reusable UI components for Survey Studio Streamlit app.

This module contains composable building blocks for the header, sidebar sections,
progress indicator, empty states, and footer. Keep logic minimal and focused on
presentation to maintain clean separation of concerns.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # TCH003: heavy typing imports behind TYPE_CHECKING
    from collections.abc import Iterable

import streamlit as st


def header(title: str = "Survey Studio", tagline: str | None = None) -> None:
    """Render the app header with title, tagline, and GitHub link."""
    if tagline is None:
        tagline = "Multi-agent literature review assistant for rigorous academic research"

    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(
            f"""
            <div style="margin-bottom: 0.25rem;">
              <h1 style="margin-bottom: 0;">📚 {title}</h1>
              <p style="margin-top: 0.25rem; color: var(--text-color, #374151);">
                {tagline}
              </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.link_button(
            "GitHub",
            "https://github.com/Aditya-gam/survey-studio",
            help="Open the repository",
            use_container_width=True,
            type="secondary",
        )


def sidebar_about() -> None:
    """Render About section in the sidebar."""
    with st.sidebar.expander("ℹ️ About", expanded=False):
        st.markdown(
            """
            **Survey Studio** helps researchers synthesize literature with AI agents.

            - Searches arXiv for relevant papers
            - Summarizes findings into a structured review
            - Exports to Markdown or HTML
            """
        )


def sidebar_troubleshooting() -> None:
    """Render Troubleshooting section in the sidebar."""
    with st.sidebar.expander("🛠️ Troubleshooting", expanded=False):
        st.markdown(
            """
            - Ensure `OPENAI_API_KEY` is set
            - Try fewer papers or a simpler topic
            - Check model/service status if requests fail
            - Review validation messages for guidance
            """
        )


def progress_steps(current_step: str, steps: Iterable[str]) -> None:
    """Render a subtle step indicator for multi-stage operations."""
    step_list = list(steps)
    cols = st.columns(len(step_list))
    for idx, step in enumerate(step_list):
        is_active = step == current_step
        label = f"**{step}**" if is_active else step
        with cols[idx]:
            st.progress(1.0 if is_active else 0.0, text=label)


def empty_state() -> None:
    """Render an engaging empty state with guidance and examples."""
    st.info("📝 Enter a research topic in the navbar above to get started.", icon="🧭")
    with st.expander("Examples", expanded=False):
        st.markdown(
            """
            Try topics like:
            - Transformer architectures for long-context reasoning
            - Applications of diffusion models in medical imaging
            - Quantum error correction techniques 2018–2024
            """
        )


def footer(app_version: str, commit_sha_short: str | None = None) -> None:
    """Render a persistent footer with version info and links."""
    sha_display = commit_sha_short or "unknown"
    st.markdown(
        f"""
        <hr/>
        <div style="
            display: flex; gap: 1rem; flex-wrap: wrap;
            align-items: center; margin-top: 3rem;
        ">
          <span>Version: <code>{app_version}</code></span>
          <span>Commit: <code>{sha_display}</code></span>
          <a href="https://github.com/Aditya-gam/survey-studio/blob/main/CHANGELOG.md"
             target="_blank">Changelog</a>
          <span style="margin-left: auto;">© 2025 Survey Studio · MIT License</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def navbar_spacer() -> None:
    """Render a spacer to account for fixed navbar positioning."""
    st.markdown(
        """
        <div style="height: 64px; margin-bottom: 20px;"></div>
        """,
        unsafe_allow_html=True,
    )


# Constants for status indicator
MAX_TOPIC_DISPLAY_LENGTH = 30


def navbar_status_indicator(topic: str, papers: int, model: str, is_valid: bool) -> None:
    """Render a status indicator for the navbar form validation."""
    if not topic:
        return

    status_color = "green" if is_valid else "red"
    status_icon = "✅" if is_valid else "❌"

    st.markdown(
        f"""
        <div style="
            position: fixed;
            top: 70px;
            right: 20px;
            background: rgba(255, 255, 255, 0.95);
            padding: 8px 16px;
            border-radius: 8px;
            border-left: 3px solid {status_color};
            font-size: 0.8rem;
            z-index: 1000;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        ">
            {status_icon} Topic: {topic[:MAX_TOPIC_DISPLAY_LENGTH]}{
            "..." if len(topic) > MAX_TOPIC_DISPLAY_LENGTH else ""
        } |
            Papers: {papers} | Model: {model}
        </div>
        """,
        unsafe_allow_html=True,
    )


def mobile_search_fab(on_click_js: str = "") -> None:
    """Render a floating action button for mobile search."""
    st.markdown(
        f"""
        <div id="mobile-search-fab" style="
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 56px;
            height: 56px;
            background: #1976d2;
            border-radius: 50%;
            display: none;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            z-index: 1000;
        " onclick="{on_click_js}">
            <span style="color: white; font-size: 24px;">🔍</span>
        </div>

        <script>
        function toggleMobileFab() {{
            const fab = document.getElementById('mobile-search-fab');
            if (window.innerWidth <= 768) {{
                fab.style.display = 'flex';
            }} else {{
                fab.style.display = 'none';
            }}
        }}

        window.addEventListener('resize', toggleMobileFab);
        toggleMobileFab();
        </script>
        """,
        unsafe_allow_html=True,
    )
