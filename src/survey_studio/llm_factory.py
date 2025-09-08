"""LLM client factory supporting multiple AI providers with fallback logic."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from autogen_ext.models.openai import OpenAIChatCompletionClient

from .config import AIProvider, get_best_available_provider
from .errors import AgentCreationError, ConfigurationError
from .logging import log_error_with_details, with_context

if TYPE_CHECKING:
    from .config import ProviderConfig

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
logger.propagate = False


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
                "No AI providers are available. Please configure at least one API key.",
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


def get_provider_info() -> dict[str, Any]:
    """Get information about available providers.

    Returns:
        Dictionary with provider information including availability and limits
    """
    from .config import get_available_providers

    available_providers = get_available_providers()

    return {
        "available_count": len(available_providers),
        "providers": [
            {
                "name": provider.provider.value,
                "model": provider.model,
                "priority": provider.priority,
                "free_tier_rpm": provider.free_tier_rpm,
                "free_tier_tpm": provider.free_tier_tpm,
            }
            for provider in available_providers
        ],
        "best_provider": available_providers[0].provider.value if available_providers else None,
    }
