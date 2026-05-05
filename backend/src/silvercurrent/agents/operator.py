"""Operator agent — the conversational ETA assistant with RAG over a curated KB.

Per `docs/agents/agent-topology.md` §3 and ADR `0006-operator-knowledge-base-design.md`.

The agent runs a bounded tool-use loop: it can call `search_knowledge_base`,
`get_user_criteria`, and `get_active_listing` up to `MAX_ITERATIONS` times before
returning a final assistant turn. Each round-trip's token usage is summed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from anthropic import AsyncAnthropic
from anthropic.types import TextBlock, ToolUseBlock
from sqlalchemy.ext.asyncio import AsyncSession

from silvercurrent.agents.tools._envelope import Envelope, fail
from silvercurrent.agents.tools.active_listing import get_active_listing
from silvercurrent.agents.tools.criteria import get_user_criteria
from silvercurrent.agents.tools.kb_search import (
    DEFAULT_K,
    MAX_K,
    format_passages_for_prompt,
    search_knowledge_base,
)
from silvercurrent.config import get_settings
from silvercurrent.db.models import ChatTurn

# Iteration cap — keeps a misbehaving model from burning unbounded tokens on
# tool calls. Five is enough for any real Operator question (search → maybe
# search again → answer).
MAX_ITERATIONS = 5
MAX_OUTPUT_TOKENS = 2048

OPERATOR_PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "operator.md"

OPERATOR_TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "search_knowledge_base",
        "description": (
            "Vector-search the curated ETA knowledge base for passages relevant to the user's question. "
            "Use this aggressively before answering substantive questions about financing, deal mechanics, "
            "due diligence, closing, or transition."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural-language query to search for. Be specific.",
                },
                "k": {
                    "type": "integer",
                    "description": f"Number of passages to retrieve (default {DEFAULT_K}, max {MAX_K}).",
                    "default": DEFAULT_K,
                    "minimum": 1,
                    "maximum": MAX_K,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_user_criteria",
        "description": (
            "Return the buyer's stated acquisition criteria (industry, geography, SDE band, etc.) "
            "from `docs/criteria.md`. Some sections may still contain `<TODO>` placeholders — treat "
            "those as 'not yet decided', not as missing data."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_active_listing",
        "description": (
            "Return the listing currently being discussed, if the chat is scoped to one. "
            "In global chat, returns `{listing: null}` — don't call this unless you actually need "
            "deal-specific context."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
]


@dataclass(frozen=True)
class AgentUsage:
    """Accumulated Anthropic API usage across all messages.create calls in one run."""

    input_tokens: int
    output_tokens: int
    model: str


@dataclass(frozen=True)
class AgentResult:
    """Final result of an Operator run: text response + usage + iteration count."""

    content: str
    usage: AgentUsage
    iterations: int


def _load_system_prompt() -> str:
    """Read the operator system prompt from `prompts/operator.md`."""
    return OPERATOR_PROMPT_PATH.read_text(encoding="utf-8")


def _format_history(turns: list[ChatTurn]) -> list[dict[str, Any]]:
    """Convert ChatTurn rows into the Anthropic messages shape (role: user|assistant)."""
    out: list[dict[str, Any]] = []
    for t in turns:
        if t.role not in ("user", "assistant"):
            continue
        out.append({"role": t.role, "content": t.content})
    return out


class OperatorAgent:
    """Stateless tool-loop runner for the Operator agent."""

    def __init__(
        self,
        *,
        client: AsyncAnthropic | None = None,
        session: AsyncSession | None = None,
        model: str | None = None,
    ) -> None:
        settings = get_settings()
        self._client = client or AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._session = session
        # Operator runs on Sonnet per topology §6.
        self._model = model or "claude-sonnet-4-6"

    async def run(
        self,
        *,
        user_message: str,
        history: list[ChatTurn],
        listing_id: UUID | None = None,
    ) -> AgentResult:
        """Run one user turn through the Operator and return the final assistant text."""
        system_prompt = _load_system_prompt()
        messages: list[dict[str, Any]] = [
            *_format_history(history),
            {"role": "user", "content": user_message},
        ]

        cumulative_input = 0
        cumulative_output = 0

        for iteration in range(1, MAX_ITERATIONS + 1):
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=MAX_OUTPUT_TOKENS,
                system=system_prompt,
                tools=OPERATOR_TOOL_SCHEMAS,  # type: ignore[arg-type]
                messages=messages,  # type: ignore[arg-type]
            )
            cumulative_input += response.usage.input_tokens
            cumulative_output += response.usage.output_tokens

            tool_uses = [b for b in response.content if isinstance(b, ToolUseBlock)]
            if not tool_uses:
                text = "".join(b.text for b in response.content if isinstance(b, TextBlock)).strip()
                return AgentResult(
                    content=text,
                    usage=AgentUsage(
                        input_tokens=cumulative_input,
                        output_tokens=cumulative_output,
                        model=self._model,
                    ),
                    iterations=iteration,
                )

            # Append the assistant's tool-use message so the model sees its own call history.
            messages.append({"role": "assistant", "content": response.content})

            # Execute each requested tool, collect results.
            tool_result_blocks: list[dict[str, Any]] = []
            for tu in tool_uses:
                envelope = await self._execute_tool(tu.name, tu.input, listing_id=listing_id)
                tool_result_blocks.append(self._envelope_to_tool_result(tu.id, tu.name, envelope))
            messages.append({"role": "user", "content": tool_result_blocks})

        # Hit the iteration cap without producing a final answer.
        return AgentResult(
            content=(
                "I called tools repeatedly without converging on an answer. "
                "Try rephrasing the question or breaking it into smaller pieces."
            ),
            usage=AgentUsage(
                input_tokens=cumulative_input,
                output_tokens=cumulative_output,
                model=self._model,
            ),
            iterations=MAX_ITERATIONS,
        )

    async def _execute_tool(
        self,
        name: str,
        tool_input: dict[str, Any],
        *,
        listing_id: UUID | None,
    ) -> Envelope:
        """Dispatch a tool call to the right implementation."""
        if name == "search_knowledge_base":
            return await search_knowledge_base(
                query=str(tool_input.get("query", "")),
                k=int(tool_input.get("k", DEFAULT_K)),
            )
        if name == "get_user_criteria":
            return await get_user_criteria()
        if name == "get_active_listing":
            if self._session is None:
                return fail("agent has no DB session; cannot fetch listing")
            return await get_active_listing(listing_id=listing_id, session=self._session)
        return fail(f"unknown tool: {name}")

    @staticmethod
    def _envelope_to_tool_result(
        tool_use_id: str,
        tool_name: str,
        envelope: Envelope,
    ) -> dict[str, Any]:
        """Format an `Envelope` as the tool_result block the Anthropic API expects.

        For `search_knowledge_base` results, retrieved passages are wrapped in
        `<retrieved_passage>` tags per ADR 0002 before being returned to the model.
        """
        if not envelope.ok:
            return {
                "type": "tool_result",
                "tool_use_id": tool_use_id,
                "content": json.dumps({"error": envelope.error or "tool failed"}),
                "is_error": True,
            }

        data = envelope.data or {}

        if tool_name == "search_knowledge_base":
            passages = data.get("passages") if isinstance(data, dict) else None
            if isinstance(passages, list):
                wrapped = format_passages_for_prompt(passages)
                content = f"Retrieved {len(passages)} passages for query {json.dumps(data.get('query'))}:\n\n{wrapped}"
            else:
                content = json.dumps(data)
        else:
            content = json.dumps(data)

        return {
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "content": content,
        }
