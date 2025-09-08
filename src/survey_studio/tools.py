"""Tool definitions and arXiv search utilities with retry mechanisms."""

from __future__ import annotations

import logging
from typing import Any

import arxiv  # type: ignore
from autogen_core.tools import FunctionTool

from .errors import ArxivSearchError, ExternalServiceError
from .logging import log_error_with_details, with_context
from .retry import retry_arxiv_operations

logger = logging.getLogger(__name__)
# Isolate this module's logger to avoid MagicMock level comparisons during tests
logger.addHandler(logging.NullHandler())
logger.propagate = False

# Constants
MAX_ARXIV_RESULTS = 50


@retry_arxiv_operations
def arxiv_search(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """Return a compact list of arXiv papers matching the query with retry mechanisms.

    Each element contains: title, authors, published, summary and pdf_url.
    Raises ArxivSearchError for failures. Includes automatic retries with backoff.
    """

    log = with_context(logger, tool_name="arxiv_search", component="tools")

    try:
        logger.info(
            "Starting arXiv search",
            extra={
                "extra_fields": {
                    "query": query[:100],  # Truncate long queries for logging
                    "max_results": max_results,
                    "operation": "arxiv_search",
                }
            },
        )

        # Validate inputs
        if not query or not query.strip():
            raise ExternalServiceError(
                "Empty query provided to arXiv search",
                service="arXiv",
                context={"query": query, "max_results": max_results},
            )

        if max_results <= 0 or max_results > MAX_ARXIV_RESULTS:
            raise ExternalServiceError(
                f"Invalid max_results: {max_results}. "
                + f"Must be between 1 and {MAX_ARXIV_RESULTS}",
                service="arXiv",
                context={"query": query, "max_results": max_results},
            )

        client = arxiv.Client()
        search = arxiv.Search(
            query=query.strip(),
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance,
        )

        papers: list[dict[str, Any]] = []
        result_count = 0

        try:
            for result in client.results(search):
                result_count += 1
                papers.append(
                    {
                        "title": result.title.strip(),
                        "authors": [a.name for a in result.authors],
                        "published": result.published.strftime("%Y-%m-%d"),
                        "summary": result.summary.strip(),
                        "pdf_url": result.pdf_url,
                        "entry_id": result.entry_id,
                        "categories": result.categories,
                    }
                )

                # Log progress for long-running searches
                if result_count % 10 == 0:
                    logger.debug(
                        f"Processed {result_count} results",
                        extra={
                            "extra_fields": {
                                "processed": result_count,
                                "target": max_results,
                            }
                        },
                    )

        except Exception as search_exc:
            # Log error details once per search
            log_error_with_details(
                logger,
                search_exc,
                "arxiv_results_iteration",
                "tools",
                query=query[:100],
                max_results=max_results,
            )
            raise ArxivSearchError(
                f"Failed to process arXiv search results: {str(search_exc)}",
                original_exception=search_exc,
                context={
                    "query": query,
                    "max_results": max_results,
                    "results_processed": result_count,
                },
            ) from search_exc

        # Emit a single info-level completion event via contextual logger for tests
        log.info(
            "arXiv search completed successfully",
            extra={
                "extra_fields": {
                    "count": len(papers),
                    "query": query[:100],
                    "duration_ms": None,  # Would be filled by retry decorator
                    "operation": "arxiv_search",
                }
            },
        )

        if not papers:
            log.warning(
                "No papers found for query",
                extra={"extra_fields": {"query": query[:100], "max_results": max_results}},
            )

        return papers

    except ExternalServiceError:
        # Re-raise ExternalServiceError as-is (already properly formatted)
        raise
    except Exception as exc:  # noqa: BLE001 - surface as domain error
        # Always log once here; retry policy avoids re-entering for generic Exception
        log_error_with_details(
            logger,
            exc,
            "arxiv_search",
            "tools",
            query=query[:100],
            max_results=max_results,
        )
        # Convert to ExternalServiceError for consistency
        raise ArxivSearchError(
            f"Failed to fetch results from arXiv: {str(exc)}",
            original_exception=exc,
            context={"query": query, "max_results": max_results, "no_retry": True},
        ) from exc


arxiv_tool = FunctionTool(
    arxiv_search,
    description=(
        "Searches arXiv and returns up to max_results papers, each containing "
        "title, authors, publication date, abstract, and pdf_url."
    ),
)
