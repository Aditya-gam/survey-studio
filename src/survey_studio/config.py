"""Configuration management for Survey Studio.

Handles loading of secrets from multiple sources in priority order:
1. Environment variables (highest priority)
2. .env file (loaded by dotenv)
3. Streamlit secrets (for hosted deployment)
"""

import os

from dotenv import load_dotenv
import streamlit as st

# Load environment variables from .env file
load_dotenv()


def get_openai_api_key() -> str | None:
    """Get OpenAI API key from multiple sources in priority order.

    Priority order:
    1. Environment variable OPENAI_API_KEY
    2. .env file (loaded by dotenv)
    3. Streamlit secrets (for hosted deployment)

    Returns:
        API key if found, None otherwise
    """
    # 1. Check environment variable (highest priority)
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key and api_key.strip():
        return api_key.strip()

    # 2. Check Streamlit secrets (for hosted deployment)
    try:
        if hasattr(st, "secrets") and "OPENAI_API_KEY" in st.secrets:
            api_key = st.secrets["OPENAI_API_KEY"]
            if api_key and api_key.strip():
                return api_key.strip()
    except Exception:
        # Streamlit secrets might not be available in all contexts
        pass

    return None


def get_openai_model() -> str:
    """Get OpenAI model from configuration sources.

    Returns:
        Model name, defaults to 'gpt-4o-mini'
    """
    # Check environment variable first
    model = os.getenv("OPENAI_MODEL")
    if model and model.strip():
        return model.strip()

    # Check Streamlit secrets
    try:
        if hasattr(st, "secrets") and "OPENAI_MODEL" in st.secrets:
            model = st.secrets["OPENAI_MODEL"]
            if model and model.strip():
                return model.strip()
    except Exception:
        pass

    return "gpt-4o-mini"


def get_max_papers() -> int:
    """Get maximum papers from configuration sources.

    Returns:
        Maximum papers, defaults to 5
    """
    # Check environment variable first
    max_papers = os.getenv("MAX_PAPERS")
    if max_papers and max_papers.strip():
        try:
            return int(max_papers.strip())
        except ValueError:
            pass

    # Check Streamlit secrets
    try:
        if hasattr(st, "secrets") and "MAX_PAPERS" in st.secrets:
            max_papers = st.secrets["MAX_PAPERS"]
            if max_papers:
                try:
                    return int(max_papers)
                except ValueError:
                    pass
    except Exception:
        pass

    return 5
