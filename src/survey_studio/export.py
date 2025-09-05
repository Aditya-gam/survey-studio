"""Export utilities (initial placeholders).

Provides simple interfaces for exporting results. This will evolve, but we
include a minimal Markdown export now to support a download action.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # TCH003: restrict heavy typing imports to type-checking time
    from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class Paper:
    title: str
    authors: list[str]
    published: str
    summary: str
    pdf_url: str


def to_markdown(topic: str, generated_text_frames: Iterable[str]) -> str:
    """Return a Markdown string combining streamed generated frames.

    This is a simple concatenation; callers may provide already-marked-up
    content. The function exists to provide a stable export interface.
    """

    header = f"# Literature Review: {topic}\n\n"
    body = "\n".join(generated_text_frames)
    return header + body + "\n"
