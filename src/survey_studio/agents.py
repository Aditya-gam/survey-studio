"""Agent builders and model client factory."""

from __future__ import annotations

import logging

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient

from .errors import AgentCreationError
from .logging import with_context
from .tools import arxiv_tool

logger = logging.getLogger(__name__)


def make_llm_client(model: str, api_key: str) -> OpenAIChatCompletionClient:
    """Create and return an OpenAI chat completion client.

    Raises AgentCreationError if initialization fails.
    """

    try:
        return OpenAIChatCompletionClient(model=model, api_key=api_key)
    except Exception as exc:  # noqa: BLE001
        raise AgentCreationError("Failed to create LLM client") from exc


def build_team(model: str, api_key: str) -> RoundRobinGroupChat:
    """Create and return the two-agent team configured for the review."""

    log = with_context(logger, component="agents")
    llm_client = make_llm_client(model=model, api_key=api_key)

    search_agent = AssistantAgent(
        name="search_agent",
        description="Crafts arXiv queries and retrieves candidate papers.",
        system_message=(
            "Given a user topic, think of the best arXiv query and call the "
            "provided tool. Always fetch five-times the papers requested so "
            "that you can down-select the most relevant ones. When the tool "
            "returns, choose exactly the number of papers requested and pass "
            "them as concise JSON to the summarizer."
        ),
        tools=[arxiv_tool],
        model_client=llm_client,
        reflect_on_tool_use=True,
    )

    summarizer = AssistantAgent(
        name="summarizer",
        description="Produces a short Markdown review from provided papers.",
        system_message=(
            "You are an expert researcher. When you receive the JSON list of "
            "papers, write a literature-review style report in Markdown:\n"
            "1. Start with a 2–3 sentence introduction of the topic.\n"
            "2. Then include one bullet per paper with: title (as Markdown "
            "link), authors, the specific problem tackled, and its key "
            "contribution.\n"
            "3. Close with a single-sentence takeaway."
        ),
        model_client=llm_client,
    )

    team = RoundRobinGroupChat(participants=[search_agent, summarizer], max_turns=2)
    log.info("team built", extra={"extra_fields": {"participants": 2}})
    return team
