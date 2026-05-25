"""Pydantic schemas for the chat API."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ChatRole = Literal["user", "assistant"]
RoutedAgent = Literal["operator", "analyst", "clarify", "out_of_scope"]


class ChatRequest(BaseModel):
    """Body for `POST /api/chat`."""

    scope: str = Field(..., min_length=1, max_length=128)
    message: str = Field(..., min_length=1, max_length=10_000)


class ChatTurnRead(BaseModel):
    """One persisted chat turn."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    scope: str
    role: ChatRole
    content: str
    created_at: datetime


class ChatUsage(BaseModel):
    """Cumulative LLM usage for a chat exchange (across all tool-loop iterations)."""

    input_tokens: int
    output_tokens: int
    model: str
    iterations: int


class RoutingInfo(BaseModel):
    """Router's classification decision for this turn."""

    agent: RoutedAgent
    rationale: str
    model: str
    input_tokens: int
    output_tokens: int


class ChatResponse(BaseModel):
    """Response body for `POST /api/chat`."""

    user_turn: ChatTurnRead
    assistant_turn: ChatTurnRead
    agent_used: RoutedAgent
    usage: ChatUsage
    routing: RoutingInfo


class ConversationRead(BaseModel):
    """One conversation in the global Chat page — a grouping of turns by scope.

    Surfaces only non-listing scopes (legacy `global` and user-created
    `chat:<uuid>`). Listing-scoped chats are their own workspace per listing
    and aren't surfaced here.
    """

    scope: str
    title: str
    turn_count: int
    first_at: datetime
    last_at: datetime
