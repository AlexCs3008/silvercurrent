"""HTTP routes for the chat API.

Phase 3 slice 2: scope is one of `global` or `listing:<uuid>`. The Router
classifies each user turn into operator / analyst / clarify / out_of_scope,
and the endpoint dispatches accordingly. clarify and out_of_scope routes
return canned text from the Router itself — no specialist runs.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, or_, select
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
    ConversationRead,
    RoutingInfo,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

# How many prior turns to feed back to the agent as conversation history.
HISTORY_LIMIT = 20

LISTING_SCOPE_PREFIX = "listing:"
CHAT_SCOPE_PREFIX = "chat:"


def _parse_scope(scope: str) -> UUID | None:
    """Return the listing id parsed from `scope`, or `None` for non-listing scopes.

    Accepts:
      - `global`              — legacy single global conversation
      - `chat:<uuid>`         — user-created conversation on the Chat page
      - `listing:<uuid>`      — listing-scoped conversation

    Raises HTTPException(400) for unsupported scope formats. Both `global` and
    `chat:*` return None — they have no listing context for the Router.
    """
    if scope == "global":
        return None
    if scope.startswith(CHAT_SCOPE_PREFIX):
        raw = scope[len(CHAT_SCOPE_PREFIX) :]
        try:
            UUID(raw)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"invalid chat id in scope '{scope}': {e}",
            ) from e
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
        detail=(
            f"scope '{scope}' is not supported. "
            "Use 'global', 'chat:<uuid>', or 'listing:<uuid>'."
        ),
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


# Max length of a derived conversation title (chars). Chosen to fit the rail.
_TITLE_MAX = 60


def _derive_title(content: str) -> str:
    """First user message, whitespace-collapsed, truncated."""
    flat = " ".join(content.split())
    if len(flat) <= _TITLE_MAX:
        return flat
    return flat[: _TITLE_MAX - 1].rstrip() + "…"


@router.get("/conversations", response_model=list[ConversationRead])
async def list_conversations(session: SessionDep) -> list[ConversationRead]:
    """Group non-listing chat turns by scope and return one entry per conversation.

    Includes the legacy `global` scope and all `chat:<uuid>` scopes. Listing
    chats are excluded — they live on the listing detail page. Ordered by
    most-recent-activity first.
    """
    stmt = (
        select(ChatTurn)
        .where(or_(ChatTurn.scope == "global", ChatTurn.scope.like("chat:%")))
        .order_by(ChatTurn.scope.asc(), ChatTurn.created_at.asc())
    )
    rows = list((await session.execute(stmt)).scalars().all())

    by_scope: dict[str, list[ChatTurn]] = {}
    for row in rows:
        by_scope.setdefault(row.scope, []).append(row)

    out: list[ConversationRead] = []
    for scope, turns in by_scope.items():
        first_user = next((t for t in turns if t.role == "user"), None)
        title = _derive_title(first_user.content) if first_user else "Untitled"
        out.append(
            ConversationRead(
                scope=scope,
                title=title,
                turn_count=len(turns),
                first_at=turns[0].created_at,
                last_at=turns[-1].created_at,
            )
        )

    out.sort(key=lambda c: c.last_at, reverse=True)
    return out


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_scope(session: SessionDep, scope: str) -> Response:
    """Delete every turn for `scope`. Idempotent — 204 even if nothing matched."""
    if not scope:
        raise HTTPException(status_code=400, detail="scope is required")
    await session.execute(delete(ChatTurn).where(ChatTurn.scope == scope))
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
