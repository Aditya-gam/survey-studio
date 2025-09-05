"""Streamlit frontend for the literature review assistant.

A minimal Streamlit frontend for the literature‑review assistant defined in
`backend.py`.  Users enter a topic and the desired number of papers, then
watch the two‑agent conversation stream in real‑time.
"""

import asyncio
from typing import Optional

import streamlit as st

from .backend import run_survey_studio


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


def render_sidebar() -> tuple[str, int, str]:
    """Render the sidebar with configuration options."""
    st.sidebar.title("📚 Survey Studio")
    st.sidebar.markdown("Configure your literature review")
    
    # Topic input
    query = st.sidebar.text_input(
        "Research topic",
        placeholder="e.g., transformer architectures, quantum computing",
        help="Enter the research topic you want to review",
    )
    
    # Number of papers slider
    n_papers = st.sidebar.slider(
        "Number of papers",
        min_value=1,
        max_value=10,
        value=5,
        help="Select how many papers to include in the review",
    )
    
    # Model selection
    model = st.sidebar.selectbox(
        "AI Model",
        options=["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
        index=0,
        help="Choose the AI model for the agents",
    )
    
    return query, n_papers, model


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


def main() -> None:
    """Main application entry point."""
    configure_page()
    
    # Render sidebar and get configuration
    query, n_papers, model = render_sidebar()
    
    # Render main content
    render_main_content(query, n_papers, model)
    
    # Handle search button and execution
    if st.sidebar.button("🚀 Start Review", type="primary", disabled=not query):
        if not query:
            st.error("Please enter a research topic first!")
            return
        
        # Run the literature review
        with st.spinner(f"Conducting literature review on '{query}'..."):
            try:
                asyncio.run(run_review_stream(query, n_papers, model))
            except RuntimeError:
                # Fallback for when an event loop is already running
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(run_review_stream(query, n_papers, model))
        
        st.success("🎉 Literature review completed!")
        
        # Add download button for results (placeholder for future enhancement)
        st.sidebar.download_button(
            label="📥 Download Results",
            data="Literature review results would be here...",
            file_name=f"literature_review_{query.replace(' ', '_')}.md",
            mime="text/markdown",
            help="Download the literature review as a Markdown file",
        )


if __name__ == "__main__":
    main()
