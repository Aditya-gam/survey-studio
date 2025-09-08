"""Main streaming interface and team coordination."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from autogen_agentchat.messages import TextMessage

if TYPE_CHECKING:  # TCH003: heavy typing imports behind TYPE_CHECKING
    from collections.abc import AsyncGenerator

from .agents import build_team
from .errors import OrchestrationError
from .logging import configure_logging, new_session_id, set_session_id, with_context
from .validation import (
    validate_model,
    validate_num_papers,
    validate_topic,
)

logger = logging.getLogger(__name__)


async def run_survey_studio(
    topic: str,
    num_papers: int = 5,
    model: str | None = None,
    *,
    session_id: str | None = None,
) -> AsyncGenerator[str, None]:
    """Yield strings representing the conversation in real-time.

    Ensures inputs are validated, logging is configured, and a session_id is
    attached to all log statements. The output frames are formatted as
    "<role>: <content>" for UI compatibility.
    """

    # Configure logging once (idempotent)
    configure_logging()

    sid = session_id or new_session_id()
    set_session_id(sid)
    log = with_context(logger, session_id=sid, component="orchestrator")

    try:
        clean_topic = validate_topic(topic)
        clean_n = validate_num_papers(num_papers)
        # Handle "auto" model selection - don't validate it, just pass None to use best available
        clean_model = validate_model(model) if model and model != "auto" else None

        team = build_team(model=clean_model)
        task_prompt = (
            f"Conduct a literature review on **{clean_topic}** and return exactly "
            f"{clean_n} papers."
        )

        log.info("run_stream.start", extra={"extra_fields": {"model": clean_model}})
        async for msg in team.run_stream(task=task_prompt):
            if isinstance(msg, TextMessage):
                yield f"{msg.source}: {msg.content}"
        log.info("run_stream.end")
    except Exception as exc:  # noqa: BLE001
        log.error("orchestration failed", extra={"extra_fields": {"error": str(exc)}})
        raise OrchestrationError("Failed to run literature review") from exc
