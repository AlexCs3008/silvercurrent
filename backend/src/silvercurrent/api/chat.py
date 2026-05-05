"""HTTP routes for the chat API.

In Phase 2 (slice 2), only `scope="global"` is supported and dispatches directly
to the Operator agent. Phase 3 introduces the Router and listing-scoped chats.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from silvercurrent.agents.operator import OperatorAgent
from silvercurrent.db.models import ChatTurn
from silvercurrent.db.session import get_session
from silvercurrent.schemas.chat import ChatRequest, ChatResponse, ChatTurnRead, ChatUsage

router = APIRouter(prefix="/api/chat", tags=["chat"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

# How many prior turns to feed back to the agent as conversation history.
HISTORY_LIMIT = 20


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
    """Run a user message through the Operator and persist both turns.

    For Phase 2 only `scope="global"` is supported. Listing-scoped chat plus
    Router dispatch land in Phase 3.
    """
    if payload.scope != "global":
        raise HTTPException(
            status_code=400,
            detail=(
                f"scope '{payload.scope}' is not supported yet. "
                "Phase 2 supports only scope='global'; listing chat lands in Phase 3."
            ),
        )

    # Load existing history (excluding the about-to-be-persisted user turn).
    history_stmt = (
        select(ChatTurn)
        .where(ChatTurn.scope == payload.scope)
        .order_by(ChatTurn.created_at.desc())
        .limit(HISTORY_LIMIT)
    )
    result = await session.execute(history_stmt)
    history_desc = list(result.scalars().all())
    history = list(reversed(history_desc))  # back to oldest-first for the agent

    agent = OperatorAgent(session=session)
    agent_result = await agent.run(user_message=payload.message, history=history)

    # Persist both turns in a single transaction.
    user_turn = ChatTurn(scope=payload.scope, role="user", content=payload.message)
    assistant_turn = ChatTurn(scope=payload.scope, role="assistant", content=agent_result.content)
    session.add(user_turn)
    session.add(assistant_turn)
    await session.commit()
    await session.refresh(user_turn)
    await session.refresh(assistant_turn)

    return ChatResponse(
        user_turn=ChatTurnRead.model_validate(user_turn),
        assistant_turn=ChatTurnRead.model_validate(assistant_turn),
        usage=ChatUsage(
            input_tokens=agent_result.usage.input_tokens,
            output_tokens=agent_result.usage.output_tokens,
            model=agent_result.usage.model,
            iterations=agent_result.iterations,
        ),
    )
