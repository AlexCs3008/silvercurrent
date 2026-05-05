"""Router agent — Haiku classifier that picks operator/analyst/clarify/out_of_scope.

Per `docs/agents/agent-topology.md` §2 and Phase 3 slice 2. Pure classification,
no tool execution. Uses forced tool-use to extract structured output: the model
must call the `route` tool, and we read the tool input as the routing decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

from anthropic import AsyncAnthropic
from anthropic.types import ToolUseBlock

from silvercurrent.config import get_settings

ROUTER_PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "router.md"
ROUTER_MODEL = "claude-haiku-4-5-20251001"
ROUTER_MAX_TOKENS = 512

RoutingTarget = Literal["operator", "analyst", "clarify", "out_of_scope"]

_ROUTE_TOOL: dict[str, Any] = {
    "name": "route",
    "description": "Record the routing decision for this user message. Always call this exactly once.",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent": {
                "type": "string",
                "enum": ["operator", "analyst", "clarify", "out_of_scope"],
                "description": "Which specialist (or special route) handles this message.",
            },
            "rationale": {
                "type": "string",
                "description": "One-sentence explanation of why this route was chosen.",
            },
            "clarification_question": {
                "type": "string",
                "description": "Required when agent == 'clarify'. One sentence the user sees.",
            },
            "out_of_scope_reply": {
                "type": "string",
                "description": "Required when agent == 'out_of_scope'. Friendly redirect shown verbatim.",
            },
        },
        "required": ["agent", "rationale"],
    },
}


@dataclass(frozen=True)
class RouterUsage:
    """Anthropic API usage from a single Router classification."""

    input_tokens: int
    output_tokens: int
    model: str


@dataclass(frozen=True)
class RoutingDecision:
    """Structured Router output."""

    agent: RoutingTarget
    rationale: str
    clarification_question: str | None
    out_of_scope_reply: str | None
    usage: RouterUsage


def _load_system_prompt() -> str:
    return ROUTER_PROMPT_PATH.read_text(encoding="utf-8")


class RouterAgent:
    """Stateless Haiku-backed classifier."""

    def __init__(
        self,
        *,
        client: AsyncAnthropic | None = None,
        model: str | None = None,
    ) -> None:
        settings = get_settings()
        self._client = client or AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._model = model or ROUTER_MODEL

    async def route(
        self,
        *,
        user_message: str,
        listing_id: UUID | None,
    ) -> RoutingDecision:
        """Classify a user message into a routing target.

        The Router sees the user's message plus a structured context block
        indicating whether a listing is in scope. Chat history is NOT passed —
        routing decisions are based on the current message; a follow-up can
        re-route if the topic shifts.
        """
        system_prompt = _load_system_prompt()
        listing_context = (
            f"Active listing in scope: {listing_id}"
            if listing_id is not None
            else "Active listing in scope: NONE (global chat)."
        )
        framed_message = f"{listing_context}\n\nUser message:\n{user_message}"

        response = await self._client.messages.create(  # type: ignore[call-overload]
            model=self._model,
            max_tokens=ROUTER_MAX_TOKENS,
            system=system_prompt,
            tools=[_ROUTE_TOOL],
            tool_choice={"type": "tool", "name": "route"},
            messages=[{"role": "user", "content": framed_message}],
        )

        tool_use = next((b for b in response.content if isinstance(b, ToolUseBlock)), None)
        if tool_use is None:
            # Forced tool-use should make this unreachable, but fall back safely.
            return RoutingDecision(
                agent="clarify",
                rationale="Router did not return a routing decision; treating as ambiguous.",
                clarification_question="Could you rephrase what you'd like help with?",
                out_of_scope_reply=None,
                usage=RouterUsage(
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                    model=self._model,
                ),
            )

        decision_input = tool_use.input if isinstance(tool_use.input, dict) else {}
        agent_raw = str(decision_input.get("agent", "clarify"))
        agent: RoutingTarget = (
            agent_raw  # type: ignore[assignment]
            if agent_raw in ("operator", "analyst", "clarify", "out_of_scope")
            else "clarify"
        )

        return RoutingDecision(
            agent=agent,
            rationale=str(decision_input.get("rationale", "")),
            clarification_question=(
                str(decision_input["clarification_question"])
                if "clarification_question" in decision_input and decision_input["clarification_question"]
                else None
            ),
            out_of_scope_reply=(
                str(decision_input["out_of_scope_reply"])
                if "out_of_scope_reply" in decision_input and decision_input["out_of_scope_reply"]
                else None
            ),
            usage=RouterUsage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                model=self._model,
            ),
        )
