"""Survey Studio - A multi-agent literature review assistant.

This package provides a Streamlit-based interface for conducting literature reviews
using AutoGen multi-agent conversations that search arXiv and generate summaries.
"""

from .backend import run_survey_studio

__version__ = "0.0.1"
__all__ = ["run_survey_studio"]
