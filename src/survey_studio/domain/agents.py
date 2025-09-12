"""Agent builders and model client factory with retry mechanisms."""

from __future__ import annotations

import logging

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat

from survey_studio.core.config import get_best_available_provider
from survey_studio.core.errors import AgentCreationError, ConfigurationError, LLMError
from survey_studio.core.logging import log_error_with_details, with_context
from survey_studio.domain.llm_factory import (
    create_llm_client,
    create_llm_client_with_fallback,
    get_provider_info,
)
from survey_studio.domain.retry import retry_llm_operations
from survey_studio.domain.tools import arxiv_tool

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
logger.propagate = False


@retry_llm_operations
def make_llm_client(
    model: str | None = None, api_key: str | None = None, use_fallback: bool = True
):
    """Create and return an LLM client with retry mechanisms.

    Args:
        model: The model name to use (optional, will use best available if not provided)
        api_key: The API key (optional, will use best available if not provided)
        use_fallback: Whether to use fallback mechanism if primary provider fails

    Returns:
        Configured LLM client

    Raises AgentCreationError if initialization fails. Includes automatic retries
    for transient failures and enhanced error reporting.
    """
    log = with_context(logger, component="agents", operation="make_llm_client")

    try:
        # Get the best available provider
        provider_config = get_best_available_provider()
        if provider_config is None:
            raise ConfigurationError(
                "No AI providers are available. Please configure at least one API key.",
                context={"available_providers": "none"},
            )

        # Override model if provided
        if model:
            provider_config = provider_config._replace(model=model)

        # Override API key if provided
        if api_key:
            provider_config = provider_config._replace(api_key=api_key)

        log.info(
            "Creating LLM client",
            extra={
                "extra_fields": {
                    "provider": provider_config.provider.value,
                    "model": provider_config.model,
                    "use_fallback": use_fallback,
                }
            },
        )

        # Use fallback mechanism if requested
        if use_fallback:
            client = create_llm_client_with_fallback(provider_config)
        else:
            client = create_llm_client(provider_config)

        log.info(
            "LLM client created successfully",
            extra={
                "extra_fields": {
                    "provider": provider_config.provider.value,
                    "model": provider_config.model,
                }
            },
        )

        return client

    except ConfigurationError:
        # Re-raise configuration errors as-is
        raise
    except Exception as exc:  # noqa: BLE001
        log_error_with_details(log.logger, exc, "make_llm_client", "agents")
        raise AgentCreationError(
            f"Failed to create LLM client: {str(exc)}",
            model=model or "unknown",
            original_exception=exc,
            context={"model": model, "provider": "auto"},
        ) from exc


def build_team(model: str | None = None, api_key: str | None = None) -> RoundRobinGroupChat:
    """Create and return the two-agent team configured for the review.

    Args:
        model: The model name to use for the agents (optional, will use best available)
        api_key: The API key (optional, will use best available)
    """

    # Only include component; tests expect with_context called with just component
    log = with_context(logger, component="agents")

    try:
        # Get provider info for logging
        provider_info = get_provider_info()

        # Use debug for start message to keep single info call as expected by tests
        log.debug(
            "Building agent team",
            extra={
                "extra_fields": {
                    "model": model or "auto",
                    "operation": "build_team",
                    "available_providers": provider_info["available_count"],
                    "best_provider": provider_info["best_provider"],
                }
            },
        )

        # Create LLM client with retry mechanisms
        llm_client = make_llm_client(model=model, api_key=api_key)

        # Create search agent with enhanced instructions
        search_agent = AssistantAgent(
            name="search_agent",
            description="Crafts arXiv queries and retrieves candidate papers.",
            system_message=(
                "You are an expert at searching arXiv for research papers. "
                "Given a user topic:\n"
                "1. Think of the best arXiv query terms for the topic\n"
                "2. Call the arxiv_search tool to retrieve papers\n"
                "3. Always fetch more papers than requested (up to 5x) so you "
                "can select the most relevant ones\n"
                "4. If the search fails, try a broader or different query\n"
                "5. Choose exactly the number of papers requested by the user\n"
                "6. Return them as a clean JSON list to the summarizer\n"
                "7. If no relevant papers are found, explain this to the user clearly"
            ),
            tools=[arxiv_tool],
            model_client=llm_client,
            reflect_on_tool_use=True,
        )

        # Create summarizer agent with enhanced instructions
        summarizer = AssistantAgent(
            name="summarizer",
            description="Produces comprehensive Markdown reviews from provided papers.",
            system_message=(
                "You are an expert researcher who creates high-quality "
                "literature reviews. When you receive a JSON list of papers:\n"
                "1. Start with a 2-3 sentence introduction to the research topic\n"
                "2. Create a structured review with one bullet point per paper:\n"
                "   - Title (as Markdown link to PDF if available)\n"
                "   - Authors and publication date\n"
                "   - Key problem or research question addressed\n"
                "   - Main contribution or finding\n"
                "   - Relevance to the overall topic\n"
                "3. End with a concise summary paragraph highlighting:\n"
                "   - Main themes and trends\n"
                "   - Key insights or consensus\n"
                "   - Potential gaps or future directions\n"
                "4. Use clear, academic language but keep it accessible\n"
                "5. If papers are insufficient or irrelevant, explain "
                "limitations clearly"
            ),
            model_client=llm_client,
        )

        # Create team with appropriate turn limits
        team = RoundRobinGroupChat(
            participants=[search_agent, summarizer],
            max_turns=4,  # Increased to allow for retry attempts
        )

        log.info(
            "Agent team built successfully",
            extra={
                "extra_fields": {
                    # For mocks, len(participants) may not be available;
                    # use expected constant of 2
                    "participants": 2,
                    "model": model,
                    "max_turns": 4,  # Use the constant value we set
                    "operation": "build_team",
                }
            },
        )

        return team

    except (ConfigurationError, LLMError):
        # Re-raise domain-specific errors as-is
        raise
    except Exception as exc:
        log_error_with_details(log.logger, exc, "build_team", "agents", model=model)
        raise AgentCreationError(
            f"Failed to build agent team: {str(exc)}",
            model=model,
            original_exception=exc,
            context={"model": model},
        ) from exc
