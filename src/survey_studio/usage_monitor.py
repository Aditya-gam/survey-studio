"""Usage monitoring and cost tracking for AI providers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import json
import logging
from pathlib import Path
from typing import Any

from .config import AIProvider

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
logger.propagate = False


@dataclass
class UsageRecord:
    """Record of API usage for tracking and cost analysis."""

    timestamp: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    duration_ms: int
    success: bool
    error_message: str | None = None


@dataclass
class ProviderStats:
    """Statistics for a specific provider."""

    provider: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_tokens: int
    total_cost_usd: float
    avg_duration_ms: float
    last_used: str | None = None


@dataclass
class UsageParams:
    """Parameters for recording API usage."""

    provider: AIProvider
    model: str
    input_tokens: int
    output_tokens: int
    duration_ms: int
    success: bool = True
    error_message: str | None = None


class UsageMonitor:
    """Monitor and track AI provider usage and costs."""

    def __init__(self, data_dir: Path | None = None) -> None:
        """Initialize the usage monitor.

        Args:
            data_dir: Directory to store usage data. Defaults to current directory.
        """
        super().__init__()
        self.data_dir = data_dir or Path.cwd()
        self.usage_file = self.data_dir / "usage_data.json"
        self.stats_file = self.data_dir / "usage_stats.json"
        self.usage_records: list[UsageRecord] = []

        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Load existing data
        self._load_usage_data()

    def _load_usage_data(self) -> None:
        """Load existing usage data from file."""
        try:
            if self.usage_file.exists():
                with open(self.usage_file) as f:
                    self.usage_records: list[UsageRecord] = [
                        UsageRecord(**record) for record in json.load(f)
                    ]
            else:
                self.usage_records = []
        except Exception as exc:
            logger.warning(f"Failed to load usage data: {exc}")
            self.usage_records = []

    def _save_usage_data(self) -> None:
        """Save usage data to file."""
        try:
            with open(self.usage_file, "w") as f:
                json.dump([asdict(record) for record in self.usage_records], f, indent=2)
        except Exception as exc:
            logger.error(f"Failed to save usage data: {exc}")

    def record_usage(self, params: UsageParams) -> None:
        """Record API usage for tracking and cost analysis.

        Args:
            params: Usage parameters containing all necessary data
        """
        total_tokens = params.input_tokens + params.output_tokens
        cost_usd = self._calculate_cost(
            params.provider, params.model, params.input_tokens, params.output_tokens
        )

        record = UsageRecord(
            timestamp=datetime.now(UTC).isoformat(),
            provider=params.provider.value,
            model=params.model,
            input_tokens=params.input_tokens,
            output_tokens=params.output_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            duration_ms=params.duration_ms,
            success=params.success,
            error_message=params.error_message,
        )

        self.usage_records.append(record)
        self._save_usage_data()

        message = (
            f"Recorded usage: {params.provider.value}/{params.model} - "
            f"{total_tokens} tokens, ${cost_usd:.4f}"
        )
        logger.info(
            message,
            extra={
                "extra_fields": {
                    "provider": params.provider.value,
                    "model": params.model,
                    "tokens": total_tokens,
                    "cost": cost_usd,
                    "success": params.success,
                }
            },
        )

    def _calculate_cost(
        self, provider: AIProvider, model: str, input_tokens: int, output_tokens: int
    ) -> float:
        """Calculate cost based on provider and model pricing.

        Args:
            provider: The AI provider
            model: The model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        # Pricing per 1M tokens (as of 2025)
        pricing = {
            AIProvider.TOGETHER_AI: {
                "meta-llama/Llama-3.1-8B-Instruct-Turbo": {"input": 0.20, "output": 0.20},
                "meta-llama/Llama-3.1-8B-Instruct": {"input": 0.20, "output": 0.20},
                "meta-llama/Llama-3.1-70B-Instruct-Turbo": {"input": 0.90, "output": 0.90},
            },
            AIProvider.GEMINI: {
                "gemini-2.0-flash-exp": {"input": 0.075, "output": 0.30},
                "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
                "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
            },
            AIProvider.PERPLEXITY: {
                "llama-3.1-sonar-large-128k-online": {"input": 1.00, "output": 1.00},
                "llama-3.1-sonar-small-128k-online": {"input": 0.20, "output": 0.20},
                "llama-3.1-sonar-huge-128k-online": {"input": 2.00, "output": 2.00},
            },
            AIProvider.OPENAI: {
                "gpt-4o-mini": {"input": 0.15, "output": 0.60},
                "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
                "gpt-4o": {"input": 2.50, "output": 10.00},
            },
        }

        provider_pricing = pricing.get(provider, {})
        model_pricing = provider_pricing.get(
            model, {"input": 1.00, "output": 1.00}
        )  # Default fallback

        input_cost = (input_tokens / 1_000_000) * model_pricing["input"]
        output_cost = (output_tokens / 1_000_000) * model_pricing["output"]

        return input_cost + output_cost

    def get_provider_stats(self, provider: AIProvider | None = None) -> list[ProviderStats]:
        """Get usage statistics for providers.

        Args:
            provider: Specific provider to get stats for, or None for all providers

        Returns:
            List of provider statistics
        """
        if provider:
            records = [r for r in self.usage_records if r.provider == provider.value]
        else:
            records = self.usage_records

        stats_by_provider: dict[str, ProviderStats] = {}

        for record in records:
            if record.provider not in stats_by_provider:
                stats_by_provider[record.provider] = ProviderStats(
                    provider=record.provider,
                    total_requests=0,
                    successful_requests=0,
                    failed_requests=0,
                    total_tokens=0,
                    total_cost_usd=0.0,
                    avg_duration_ms=0.0,
                )

            stats = stats_by_provider[record.provider]
            stats.total_requests += 1
            stats.total_tokens += record.total_tokens
            stats.total_cost_usd += record.cost_usd

            if record.success:
                stats.successful_requests += 1
            else:
                stats.failed_requests += 1

            # Update last used timestamp
            if not stats.last_used or record.timestamp > stats.last_used:
                stats.last_used = record.timestamp

        # Calculate averages
        for stats in stats_by_provider.values():
            if stats.total_requests > 0:
                durations = [r.duration_ms for r in records if r.provider == stats.provider]
                stats.avg_duration_ms = sum(durations) / len(durations)

        return list(stats_by_provider.values())

    def get_total_usage(self) -> dict[str, Any]:
        """Get total usage statistics across all providers.

        Returns:
            Dictionary with total usage statistics
        """
        if not self.usage_records:
            return {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "total_tokens": 0,
                "total_cost_usd": 0.0,
                "avg_duration_ms": 0.0,
            }

        total_requests = len(self.usage_records)
        successful_requests = sum(1 for r in self.usage_records if r.success)
        failed_requests = total_requests - successful_requests
        total_tokens = sum(r.total_tokens for r in self.usage_records)
        total_cost = sum(r.cost_usd for r in self.usage_records)
        avg_duration = sum(r.duration_ms for r in self.usage_records) / total_requests

        return {
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost,
            "avg_duration_ms": avg_duration,
        }

    def export_usage_data(self, file_path: Path) -> None:
        """Export usage data to a file.

        Args:
            file_path: Path to export the data to
        """
        try:
            with open(file_path, "w") as f:
                json.dump([asdict(record) for record in self.usage_records], f, indent=2)
            logger.info(f"Usage data exported to {file_path}")
        except Exception as exc:
            logger.error(f"Failed to export usage data: {exc}")
            raise


class UsageMonitorSingleton:
    """Singleton wrapper for UsageMonitor to avoid global variables."""

    _instance: UsageMonitor | None = None

    @classmethod
    def get_instance(cls) -> UsageMonitor:
        """Get the singleton usage monitor instance."""
        if cls._instance is None:
            cls._instance = UsageMonitor()
        return cls._instance


def get_usage_monitor() -> UsageMonitor:
    """Get the global usage monitor instance.

    Returns:
        Usage monitor instance
    """
    return UsageMonitorSingleton.get_instance()


def record_api_usage(params: UsageParams) -> None:
    """Record API usage using the global usage monitor.

    Args:
        params: Usage parameters containing all necessary data
    """
    monitor = get_usage_monitor()
    monitor.record_usage(params)
