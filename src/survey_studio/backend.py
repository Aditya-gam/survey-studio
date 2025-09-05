"""Backward-compatible facade for the refactored orchestrator.

This module has been retained to avoid breaking imports in older code. New
code should import from `survey_studio.orchestrator` instead.
"""

from __future__ import annotations

from .orchestrator import run_survey_studio  # re-export

__all__ = ["run_survey_studio"]
