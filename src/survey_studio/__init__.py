"""Survey Studio - A multi-agent literature review assistant.

Public exports are intentionally minimal; prefer importing submodules directly.
"""

from . import errors as errors
from .orchestrator import run_survey_studio

__version__ = "0.0.1"
__all__ = ["run_survey_studio", "errors"]
