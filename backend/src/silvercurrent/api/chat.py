"""HTTP routes for the chat API.

Phase 3 slice 2: scope is one of `global` or `listing:<uuid>`. The Router
classifies each user turn into operator / analyst / clarify / out_of_scope,
and the endpoint dispatches accordingly. clarify and out_of_scope routes
return canned text from the Router itself — no specialist runs.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from silvercurrent.agents.analyst import AnalystAgent
from silvercurrent.agents.operator import OperatorAgent
from silvercurrent.agents.router import RouterAgent, RoutingDecision
from silvercurrent.db.models import ChatTurn, Listing
from silvercurrent.db.session import get_session
from silvercurrent.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChatTurnRead,
    ChatUsage,
    RoutingInfo,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

# How many prior turns to feed back to the agent as conversation history.
HISTORY_LIMIT = 20

LISTING_SCOPE_PREFIX = "listing:"


def _parse_scope(scope: str) -> UUID | None:
    """Return the listing id parsed from `scope`, or `None` for global scope.

    Raises HTTPException(400) for unsupported scope formats.
    """
    if scope == "global":
        return None
    if scope.startswith(LISTING_SCOPE_PREFIX):
        raw = scope[len(LISTING_SCOPE_PREFIX) :]
        try:
            return UUID(raw)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"invalid listing id in scope '{scope}': {e}",
            ) from e
    raise HTTPException(
        status_code=400,
        detail=(f"scope '{scope}' is not supported. Use 'global' or 'listing:<uuid>'."),
    )


@router.get("", response_model=list[ChatTurnRead])
async def list_chat_turns(
    session: SessionDep,
    scope: str = "global",
) -> list[ChatTurn]:
    """Return persisted chat turns for the given `scope`, oldest first."""
    stmt = select(ChatTurn).where(ChatTurn.scope == scope).order_by(ChatTurn.created_at.asc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.post("", response_model=ChatResponse)
async def post_chat(payload: ChatRequest, session: SessionDep) -> ChatResponse:
    """Run a user message through the Router → specialist and persist both turns."""
    listing_id = _parse_scope(payload.scope)
    if listing_id is not None:
        listing = await session.get(Listing, listing_id)
        if listing is None:
            raise HTTPException(
                status_code=404,
                detail=f"listing {listing_id} not found",
            )

    # Load existing history for this scope (excluding the about-to-be-persisted user turn).
    history_stmt = (
        select(ChatTurn)
        .where(ChatTurn.scope == payload.scope)
        .order_by(ChatTurn.created_at.desc())
        .limit(HISTORY_LIMIT)
    )
    result = await session.execute(history_stmt)
    history_desc = list(result.scalars().all())
    history = list(reversed(history_desc))  # back to oldest-first for the agent

    # Classify.
    router_agent = RouterAgent()
    decision = await router_agent.route(user_message=payload.message, listing_id=listing_id)

    # Dispatch.
    assistant_text, specialist_usage = await _dispatch(
        decision=decision,
        user_message=payload.message,
        history=history,
        listing_id=listing_id,
        session=session,
    )

    # Persist both turns.
    user_turn = ChatTurn(scope=payload.scope, role="user", content=payload.message)
    assistant_turn = ChatTurn(scope=payload.scope, role="assistant", content=assistant_text)
    session.add(user_turn)
    session.add(assistant_turn)
    await session.commit()
    await session.refresh(user_turn)
    await session.refresh(assistant_turn)

    return ChatResponse(
        user_turn=ChatTurnRead.model_validate(user_turn),
        assistant_turn=ChatTurnRead.model_validate(assistant_turn),
        agent_used=decision.agent,
        usage=specialist_usage,
        routing=RoutingInfo(
            agent=decision.agent,
            rationale=decision.rationale,
            model=decision.usage.model,
            input_tokens=decision.usage.input_tokens,
            output_tokens=decision.usage.output_tokens,
        ),
    )


async def _dispatch(
    *,
    decision: RoutingDecision,
    user_message: str,
    history: list[ChatTurn],
    listing_id: UUID | None,
    session: AsyncSession,
) -> tuple[str, ChatUsage]:
    """Run the specialist (or canned reply) the Router selected.

    Returns the assistant text and a ChatUsage describing whichever model
    produced that text. For `clarify` / `out_of_scope`, that's the Router.
    """
    if decision.agent == "operator":
        operator_agent = OperatorAgent(session=session)
        op_result = await operator_agent.run(
            user_message=user_message,
            history=history,
            listing_id=listing_id,
        )
        return op_result.content, ChatUsage(
            input_tokens=op_result.usage.input_tokens,
            output_tokens=op_result.usage.output_tokens,
            model=op_result.usage.model,
            iterations=op_result.iterations,
        )

    if decision.agent == "analyst":
        # Defensive: Router prompt forbids `analyst` without a listing, but
        # double-check here so a misclassification can't crash on a missing id.
        if listing_id is None:
            return (
                "Analyst needs a specific listing to evaluate. Open a listing and ask there.",
                _router_usage_as_chat_usage(decision),
            )
        analyst_agent = AnalystAgent(session=session)
        an_result = await analyst_agent.chat(
            user_message=user_message,
            history=history,
            listing_id=listing_id,
        )
        return an_result.deal_sheet, ChatUsage(
            input_tokens=an_result.usage.input_tokens,
            output_tokens=an_result.usage.output_tokens,
            model=an_result.usage.model,
            iterations=an_result.iterations,
        )

    if decision.agent == "clarify":
        text = decision.clarification_question or "Could you tell me a bit more about what you're trying to figure out?"
        return text, _router_usage_as_chat_usage(decision)

    # out_of_scope
    text = decision.out_of_scope_reply or (
        "That's outside what Silvercurrent helps with — "
        "I cover ETA mechanics, deal analysis, and post-acquisition operations."
    )
    return text, _router_usage_as_chat_usage(decision)


def _router_usage_as_chat_usage(decision: RoutingDecision) -> ChatUsage:
    """Wrap a Router's usage as a ChatUsage for clarify/out_of_scope replies."""
    return ChatUsage(
        input_tokens=decision.usage.input_tokens,
        output_tokens=decision.usage.output_tokens,
        model=decision.usage.model,
        iterations=0,
    )
