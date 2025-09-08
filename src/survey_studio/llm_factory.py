"""LLM client factory supporting multiple AI providers with fallback logic."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from autogen_ext.models.openai import OpenAIChatCompletionClient

from .config import AIProvider, get_available_providers, get_best_available_provider
from .errors import AgentCreationError, ConfigurationError
from .logging import log_error_with_details, with_context

if TYPE_CHECKING:
    from .config import ProviderConfig

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
logger.propagate = False

# Constants
NO_PROVIDERS_ERROR = "No AI providers are available. Please configure at least one API key."


def create_llm_client(provider_config: ProviderConfig | None = None) -> OpenAIChatCompletionClient:
    """Create an LLM client for the specified provider.

    Args:
        provider_config: Provider configuration. If None, uses the best available provider.

    Returns:
        LLM client instance

    Raises:
        ConfigurationError: If no providers are available or configuration is invalid
        AgentCreationError: If client creation fails
    """
    log = with_context(logger, component="llm_factory", operation="create_llm_client")

    if provider_config is None:
        provider_config = get_best_available_provider()
        if provider_config is None:
            raise ConfigurationError(
                NO_PROVIDERS_ERROR,
                context={"available_providers": "none"},
            )

    try:
        log.info(
            f"Creating LLM client for {provider_config.provider.value}",
            extra={
                "extra_fields": {
                    "provider": provider_config.provider.value,
                    "model": provider_config.model,
                }
            },
        )

        # All providers use OpenAI-compatible API with different base URLs
        # We know api_key is not None at this point due to the check in get_available_providers
        assert provider_config.api_key is not None

        if provider_config.provider == AIProvider.TOGETHER_AI:
            client = OpenAIChatCompletionClient(
                model=provider_config.model,
                api_key=provider_config.api_key,
                base_url="https://api.together.xyz/v1",
            )
        elif provider_config.provider == AIProvider.GEMINI:
            client = OpenAIChatCompletionClient(
                model=provider_config.model,
                api_key=provider_config.api_key,
                base_url="https://generativelanguage.googleapis.com/v1beta",
            )
        elif provider_config.provider == AIProvider.PERPLEXITY:
            client = OpenAIChatCompletionClient(
                model=provider_config.model,
                api_key=provider_config.api_key,
                base_url="https://api.perplexity.ai",
            )
        else:  # OpenAI
            client = OpenAIChatCompletionClient(
                model=provider_config.model, api_key=provider_config.api_key
            )

        log.info(
            f"LLM client created successfully for {provider_config.provider.value}",
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
        log_error_with_details(
            log.logger,
            exc,
            "create_llm_client",
            "llm_factory",
            provider=provider_config.provider.value,
            model=provider_config.model,
        )
        raise AgentCreationError(
            f"Failed to create LLM client for {provider_config.provider.value}: {str(exc)}",
            model=provider_config.model,
            original_exception=exc,
            context={"provider": provider_config.provider.value, "model": provider_config.model},
        ) from exc


def create_llm_client_with_fallback(
    provider_config: ProviderConfig | None = None,
) -> OpenAIChatCompletionClient:
    """Create an LLM client with automatic fallback to other providers on failure.

    Args:
        provider_config: Provider configuration. If None, uses the best available provider.

    Returns:
        LLM client instance

    Raises:
        ConfigurationError: If no providers are available or configuration is invalid
        AgentCreationError: If all providers fail
    """
    log = with_context(logger, component="llm_factory", operation="create_llm_client_with_fallback")

    # Get all available providers for fallback
    available_providers: list[ProviderConfig] = get_available_providers()
    if not available_providers:
        raise ConfigurationError(
            NO_PROVIDERS_ERROR,
            context={"available_providers": "none"},
        )

    if provider_config is not None:
        # Move requested provider to front of list
        requested_provider = next(
            (p for p in available_providers if p.provider == provider_config.provider), None
        )
        if requested_provider:
            available_providers.remove(requested_provider)
            available_providers.insert(0, requested_provider)

    last_exception = None
    for current_provider in available_providers:
        try:
            log.info(
                f"Attempting to create LLM client for {current_provider.provider.value}",
                extra={
                    "extra_fields": {
                        "provider": current_provider.provider.value,
                        "model": current_provider.model,
                    }
                },
            )

            client = create_llm_client(current_provider)

            log.info(
                f"Successfully created LLM client for {current_provider.provider.value}",
                extra={
                    "extra_fields": {
                        "provider": current_provider.provider.value,
                        "model": current_provider.model,
                    }
                },
            )

            return client

        except Exception as exc:  # noqa: BLE001
            last_exception = exc
            log.warning(
                f"Failed to create LLM client for {current_provider.provider.value}: {str(exc)}",
                extra={
                    "extra_fields": {
                        "provider": current_provider.provider.value,
                        "model": current_provider.model,
                        "error": str(exc),
                    }
                },
            )
            continue

    # If we get here, all providers failed
    log.error(
        "All AI providers failed to create LLM clients",
        extra={
            "extra_fields": {
                "attempted_providers": [p.provider.value for p in available_providers],
                "last_error": str(last_exception) if last_exception else "unknown",
            }
        },
    )

    error_msg = (
        f"All AI providers failed. Last error: "
        f"{str(last_exception) if last_exception else 'unknown'}"
    )
    raise AgentCreationError(
        error_msg,
        model="unknown",
        original_exception=last_exception,
        context={"attempted_providers": [p.provider.value for p in available_providers]},
    ) from last_exception


def get_provider_info() -> dict[str, Any]:
    """Get information about available providers.

    Returns:
        Dictionary with provider information including availability, limits, and usage stats
    """
    from .config import get_available_providers
    from .usage_monitor import get_usage_monitor

    available_providers = get_available_providers()
    usage_monitor = get_usage_monitor()
    provider_stats = usage_monitor.get_provider_stats()
    total_usage = usage_monitor.get_total_usage()

    # Create a mapping of provider stats for easy lookup
    stats_map = {stats.provider: stats for stats in provider_stats}

    return {
        "available_count": len(available_providers),
        "providers": [
            {
                "name": provider.provider.value,
                "model": provider.model,
                "priority": provider.priority,
                "free_tier_rpm": provider.free_tier_rpm,
                "free_tier_tpm": provider.free_tier_tpm,
                "usage_stats": stats_map.get(
                    provider.provider.value,
                    {
                        "total_requests": 0,
                        "successful_requests": 0,
                        "failed_requests": 0,
                        "total_tokens": 0,
                        "total_cost_usd": 0.0,
                        "avg_duration_ms": 0.0,
                        "last_used": None,
                    },
                ),
            }
            for provider in available_providers
        ],
        "best_provider": available_providers[0].provider.value if available_providers else None,
        "total_usage": total_usage,
    }
