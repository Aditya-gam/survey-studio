"""Tool definitions and arXiv search utilities."""

from __future__ import annotations

import logging
from typing import Any

import arxiv
from autogen_core.tools import FunctionTool

from .errors import ArxivSearchError
from .logging import with_context

logger = logging.getLogger(__name__)


def arxiv_search(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """Return a compact list of arXiv papers matching the query.

    Each element contains: title, authors, published, summary and pdf_url.
    Raises ArxivSearchError for failures.
    """

    log = with_context(logger, tool_name="arxiv_search")
    try:
        client = arxiv.Client()
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance,
        )
        papers: list[dict[str, Any]] = []
        for result in client.results(search):
            papers.append(
                {
                    "title": result.title,
                    "authors": [a.name for a in result.authors],
                    "published": result.published.strftime("%Y-%m-%d"),
                    "summary": result.summary,
                    "pdf_url": result.pdf_url,
                }
            )
        log.info(
            "arxiv_search completed", extra={"extra_fields": {"count": len(papers)}}
        )
        return papers
    except Exception as exc:  # noqa: BLE001 - surface as domain error
        log.error("arxiv_search failed", extra={"extra_fields": {"error": str(exc)}})
        raise ArxivSearchError("Failed to fetch results from arXiv") from exc


arxiv_tool = FunctionTool(
    arxiv_search,
    description=(
        "Searches arXiv and returns up to max_results papers, each containing "
        "title, authors, publication date, abstract, and pdf_url."
    ),
)
