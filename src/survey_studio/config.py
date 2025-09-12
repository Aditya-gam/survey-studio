"""Configuration management for Survey Studio.

Handles loading of secrets from multiple sources in priority order:
1. Environment variables (highest priority)
2. .env file (loaded by dotenv)
"""

from enum import Enum
import os
from typing import NamedTuple

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class AIProvider(Enum):
    """AI providers supported by the application."""

    TOGETHER_AI = "together_ai"
    GEMINI = "gemini"
    PERPLEXITY = "perplexity"
    OPENAI = "openai"


class ProviderConfig(NamedTuple):
    """Configuration for an AI provider."""

    provider: AIProvider
    api_key: str | None
    model: str
    priority: int  # Lower number = higher priority
    free_tier_rpm: int
    free_tier_tpm: int


# Provider configurations ordered by cost efficiency and reliability (best to worst)
# Updated for 2025 with latest pricing and performance data
PROVIDER_CONFIGS = {
    AIProvider.TOGETHER_AI: ProviderConfig(
        provider=AIProvider.TOGETHER_AI,
        api_key=None,  # Will be loaded dynamically
        # Most cost-effective for general tasks
        model="meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
        priority=1,
        free_tier_rpm=60,  # Generous free tier
        free_tier_tpm=60000,
    ),
    AIProvider.GEMINI: ProviderConfig(
        provider=AIProvider.GEMINI,
        api_key=None,  # Will be loaded dynamically
        model="gemini-2.5-flash",  # Latest stable model with enhanced capabilities
        priority=2,
        free_tier_rpm=5,  # Limited but high-quality
        free_tier_tpm=250000,
    ),
    AIProvider.PERPLEXITY: ProviderConfig(
        provider=AIProvider.PERPLEXITY,
        api_key=None,  # Will be loaded dynamically
        model="llama-3.1-sonar-large-128k-online",  # Best for research with web access
        priority=3,
        free_tier_rpm=5,  # Pro tier has higher limits
        free_tier_tpm=100000,
    ),
    AIProvider.OPENAI: ProviderConfig(
        provider=AIProvider.OPENAI,
        api_key=None,  # Will be loaded dynamically
        model="gpt-4o-mini",  # Reliable fallback with good performance
        priority=4,
        free_tier_rpm=3,  # Most limited free tier
        free_tier_tpm=40000,
    ),
}


def _get_api_key(env_var: str) -> str | None:
    """Get API key from multiple sources in priority order.

    Priority order:
    1. Environment variable
    2. .env file (loaded by dotenv)

    Args:
        env_var: Environment variable name

    Returns:
        API key if found, None otherwise
    """
    # 1. Check environment variable (highest priority)
    api_key = os.getenv(env_var)
    if api_key and api_key.strip():
        return api_key.strip()

    return None


def get_openai_api_key() -> str | None:
    """Get OpenAI API key from multiple sources in priority order."""
    return _get_api_key("OPENAI_API_KEY")


def get_together_ai_api_key() -> str | None:
    """Get Together AI API key from multiple sources in priority order."""
    return _get_api_key("TOGETHER_AI_API_KEY")


def get_gemini_api_key() -> str | None:
    """Get Gemini API key from multiple sources in priority order."""
    return _get_api_key("GEMINI_API_KEY")


def get_perplexity_api_key() -> str | None:
    """Get Perplexity API key from multiple sources in priority order."""
    return _get_api_key("PERPLEXITY_API_KEY")


def get_available_providers() -> list[ProviderConfig]:
    """Get list of available AI providers with their API keys loaded.

    Returns:
        List of provider configurations with loaded API keys, ordered by priority
    """
    # Load API keys for all providers
    api_key_loaders = {
        AIProvider.TOGETHER_AI: get_together_ai_api_key,
        AIProvider.GEMINI: get_gemini_api_key,
        AIProvider.PERPLEXITY: get_perplexity_api_key,
        AIProvider.OPENAI: get_openai_api_key,
    }

    available_providers: list[ProviderConfig] = []
    for provider, config in PROVIDER_CONFIGS.items():
        api_key = api_key_loaders[provider]()
        if api_key:
            # Get the model for this provider (with override support)
            model = get_model_for_provider(provider)

            # Create a new config with the loaded API key and model
            updated_config = ProviderConfig(
                provider=config.provider,
                api_key=api_key,
                model=model,
                priority=config.priority,
                free_tier_rpm=config.free_tier_rpm,
                free_tier_tpm=config.free_tier_tpm,
            )
            available_providers.append(updated_config)

    # Sort by priority (lower number = higher priority)
    return sorted(available_providers, key=lambda x: x.priority)


def get_best_available_provider() -> ProviderConfig | None:
    """Get the best available AI provider based on free tier limits.

    Returns:
        Best available provider config, or None if no providers are available
    """
    available_providers = get_available_providers()
    return available_providers[0] if available_providers else None


def get_model_for_provider(provider: AIProvider) -> str:
    """Get model name for a specific provider from configuration sources.

    Args:
        provider: The AI provider to get model for

    Returns:
        Model name for the provider, using default if not overridden
    """
    # Map providers to their environment variable names
    env_var_map = {
        AIProvider.OPENAI: "OPENAI_MODEL",
        AIProvider.TOGETHER_AI: "TOGETHER_AI_MODEL",
        AIProvider.GEMINI: "GEMINI_MODEL",
        AIProvider.PERPLEXITY: "PERPLEXITY_MODEL",
    }

    env_var = env_var_map.get(provider)
    if not env_var:
        # Fallback to default model for the provider
        return PROVIDER_CONFIGS[provider].model

    # Check environment variable first
    model = os.getenv(env_var)
    if model and model.strip():
        return model.strip()

    # Return default model for the provider
    return PROVIDER_CONFIGS[provider].model


def get_openai_model() -> str:
    """Get OpenAI model from configuration sources.

    Returns:
        Model name, defaults to 'gpt-4o-mini'
    """
    return get_model_for_provider(AIProvider.OPENAI)


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

    return 5
