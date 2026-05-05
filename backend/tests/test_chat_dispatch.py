"""Tests for Phase 3 slice 2: Router + listing-scoped chat dispatch.

Covers:
- RouterAgent classification round-trip (forced tool-use)
- AnalystAgent.chat conversational mode
- POST /api/chat dispatch for each routing target
- Listing-scoped chat plumbing (scope parsing, listing existence check)
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from anthropic.types import TextBlock, ToolUseBlock
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from silvercurrent.agents.analyst import AnalystAgent
from silvercurrent.agents.router import RouterAgent, RouterUsage, RoutingDecision
from silvercurrent.db.models import Base, ChatTurn, Listing
from silvercurrent.db.session import get_session
from silvercurrent.main import app

# --- Mock helpers -------------------------------------------------------------


def _text_response(text: str, *, input_tokens: int = 80, output_tokens: int = 40) -> MagicMock:
    block = TextBlock(type="text", text=text, citations=None)
    response = MagicMock()
    response.content = [block]
    response.stop_reason = "end_turn"
    response.usage = MagicMock(input_tokens=input_tokens, output_tokens=output_tokens)
    return response


def _route_tool_response(
    *,
    agent: str,
    rationale: str = "test",
    clarification_question: str | None = None,
    out_of_scope_reply: str | None = None,
    input_tokens: int = 50,
    output_tokens: int = 25,
) -> MagicMock:
    """Build a Router-shaped response (forced tool-use to the `route` tool)."""
    payload: dict[str, Any] = {"agent": agent, "rationale": rationale}
    if clarification_question is not None:
        payload["clarification_question"] = clarification_question
    if out_of_scope_reply is not None:
        payload["out_of_scope_reply"] = out_of_scope_reply
    block = ToolUseBlock(type="tool_use", id="toolu_route", name="route", input=payload)
    response = MagicMock()
    response.content = [block]
    response.stop_reason = "tool_use"
    response.usage = MagicMock(input_tokens=input_tokens, output_tokens=output_tokens)
    return response


def _client_with_responses(*responses: MagicMock) -> MagicMock:
    client = MagicMock()
    client.messages = MagicMock()
    client.messages.create = AsyncMock(side_effect=list(responses))
    return client


def _force_router_to(
    agent: str,
    *,
    clarification_question: str | None = None,
    out_of_scope_reply: str | None = None,
) -> type:
    """Build a stand-in RouterAgent that always returns the given decision."""
    decision = RoutingDecision(
        agent=agent,  # type: ignore[arg-type]
        rationale="forced for test",
        clarification_question=clarification_question,
        out_of_scope_reply=out_of_scope_reply,
        usage=RouterUsage(input_tokens=12, output_tokens=8, model="test-router"),
    )

    class _FakeRouter:
        def __init__(self, *_: Any, **__: Any) -> None:
            pass

        async def route(self, **_: Any) -> RoutingDecision:
            return decision

    return _FakeRouter


def _seed_listing(session: AsyncSession, **overrides: Any) -> Listing:
    defaults: dict[str, Any] = {
        "business_name": "Acme HVAC",
        "industry": "HVAC services",
        "location": "Miami, FL",
        "asking_price": 1_200_000,
        "sde": 350_000,
        "revenue": 2_100_000,
        "narrative": "Established HVAC contractor.",
    }
    defaults.update(overrides)
    listing = Listing(**defaults)
    session.add(listing)
    return listing


# --- Fixtures -----------------------------------------------------------------


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as s:
        yield s
    await engine.dispose()


@pytest_asyncio.fixture
async def chat_client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def _override() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_session] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c
    app.dependency_overrides.clear()


# --- RouterAgent unit tests ---------------------------------------------------


@pytest.mark.asyncio
async def test_router_classifies_to_operator() -> None:
    fake_client = _client_with_responses(
        _route_tool_response(agent="operator", rationale="general SBA question, no listing")
    )
    router = RouterAgent(client=fake_client, model="test-router")

    decision = await router.route(user_message="How does an SBA 7(a) loan work?", listing_id=None)

    assert decision.agent == "operator"
    assert decision.rationale == "general SBA question, no listing"
    assert decision.clarification_question is None
    assert decision.out_of_scope_reply is None
    assert decision.usage.model == "test-router"


@pytest.mark.asyncio
async def test_router_classifies_to_analyst_when_listing_in_scope() -> None:
    fake_client = _client_with_responses(_route_tool_response(agent="analyst"))
    router = RouterAgent(client=fake_client, model="test-router")

    decision = await router.route(user_message="Is this priced fairly?", listing_id=uuid4())

    assert decision.agent == "analyst"


@pytest.mark.asyncio
async def test_router_returns_clarification_question() -> None:
    fake_client = _client_with_responses(
        _route_tool_response(
            agent="clarify",
            clarification_question="Which listing did you mean?",
        )
    )
    router = RouterAgent(client=fake_client, model="test-router")

    decision = await router.route(user_message="is this a good deal?", listing_id=None)

    assert decision.agent == "clarify"
    assert decision.clarification_question == "Which listing did you mean?"


@pytest.mark.asyncio
async def test_router_returns_out_of_scope_reply() -> None:
    fake_client = _client_with_responses(
        _route_tool_response(
            agent="out_of_scope",
            out_of_scope_reply="Silvercurrent doesn't help with that — try ETA topics.",
        )
    )
    router = RouterAgent(client=fake_client, model="test-router")

    decision = await router.route(user_message="What's the weather in Miami?", listing_id=None)

    assert decision.agent == "out_of_scope"
    assert decision.out_of_scope_reply is not None
    assert "ETA" in decision.out_of_scope_reply


@pytest.mark.asyncio
async def test_router_passes_listing_context_to_model() -> None:
    """The Router's user message must declare whether a listing is in scope."""
    fake_client = _client_with_responses(_route_tool_response(agent="analyst"))
    router = RouterAgent(client=fake_client, model="test-router")
    listing_id = uuid4()

    await router.route(user_message="thoughts?", listing_id=listing_id)

    call = fake_client.messages.create.call_args
    user_content = call.kwargs["messages"][0]["content"]
    assert str(listing_id) in user_content
    assert "Active listing in scope" in user_content


# --- AnalystAgent.chat unit tests ---------------------------------------------


@pytest.mark.asyncio
async def test_analyst_chat_short_answer(db_session: AsyncSession) -> None:
    """Conversational mode answers the question directly without producing a Deal Sheet."""
    listing = _seed_listing(db_session)
    await db_session.commit()

    fake_client = _client_with_responses(_text_response("The asking multiple is 3.43× SDE."))
    agent = AnalystAgent(client=fake_client, session=db_session, model="test-model")

    result = await agent.chat(
        user_message="What's the asking multiple?",
        history=[],
        listing_id=listing.id,
    )

    assert "3.43" in result.deal_sheet
    assert result.iterations == 1


@pytest.mark.asyncio
async def test_analyst_chat_includes_history(db_session: AsyncSession) -> None:
    """Prior chat turns are formatted as messages and prepended to the new user turn."""
    listing = _seed_listing(db_session)
    await db_session.commit()

    fake_client = _client_with_responses(_text_response("ok"))
    agent = AnalystAgent(client=fake_client, session=db_session, model="test-model")

    history = [
        ChatTurn(scope=f"listing:{listing.id}", role="user", content="prior question"),
        ChatTurn(scope=f"listing:{listing.id}", role="assistant", content="prior answer"),
    ]
    await agent.chat(user_message="follow-up", history=history, listing_id=listing.id)

    sent = fake_client.messages.create.call_args.kwargs["messages"]
    assert sent[0] == {"role": "user", "content": "prior question"}
    assert sent[1] == {"role": "assistant", "content": "prior answer"}
    assert sent[2] == {"role": "user", "content": "follow-up"}


# --- /api/chat dispatch tests -------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_routes_to_analyst_on_listing_scope(
    chat_client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When Router → analyst and scope is listing:<uuid>, the AnalystAgent.chat runs."""
    listing = _seed_listing(db_session)
    await db_session.commit()

    fake_anthropic = _client_with_responses(_text_response("Asking is 3.43× SDE."))

    import silvercurrent.api.chat as chat_module

    real_analyst = chat_module.AnalystAgent  # type: ignore[attr-defined]

    def mock_analyst(**kwargs: Any) -> Any:
        return real_analyst(client=fake_anthropic, session=kwargs.get("session"), model="test-model")

    monkeypatch.setattr(chat_module, "AnalystAgent", mock_analyst)
    monkeypatch.setattr(chat_module, "RouterAgent", _force_router_to("analyst"))

    response = await chat_client.post(
        "/api/chat",
        json={"scope": f"listing:{listing.id}", "message": "What's the multiple?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["agent_used"] == "analyst"
    assert body["assistant_turn"]["content"] == "Asking is 3.43× SDE."
    assert body["routing"]["agent"] == "analyst"


@pytest.mark.asyncio
async def test_dispatch_clarify_returns_router_question(
    chat_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """clarify route returns the Router's question; no specialist runs."""
    import silvercurrent.api.chat as chat_module

    monkeypatch.setattr(
        chat_module,
        "RouterAgent",
        _force_router_to("clarify", clarification_question="Which listing did you mean?"),
    )

    response = await chat_client.post(
        "/api/chat",
        json={"scope": "global", "message": "is this a good deal?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["agent_used"] == "clarify"
    assert body["assistant_turn"]["content"] == "Which listing did you mean?"
    assert body["usage"]["iterations"] == 0
    assert body["usage"]["model"] == "test-router"


@pytest.mark.asyncio
async def test_dispatch_out_of_scope_returns_router_reply(
    chat_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """out_of_scope route returns the Router's friendly redirect."""
    import silvercurrent.api.chat as chat_module

    monkeypatch.setattr(
        chat_module,
        "RouterAgent",
        _force_router_to(
            "out_of_scope",
            out_of_scope_reply="Silvercurrent doesn't help with weather — try an ETA question.",
        ),
    )

    response = await chat_client.post(
        "/api/chat",
        json={"scope": "global", "message": "what's the weather?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["agent_used"] == "out_of_scope"
    assert "weather" in body["assistant_turn"]["content"]


@pytest.mark.asyncio
async def test_dispatch_analyst_without_listing_falls_back(
    chat_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If the Router misclassifies global → analyst, the endpoint returns a defensive fallback."""
    import silvercurrent.api.chat as chat_module

    monkeypatch.setattr(chat_module, "RouterAgent", _force_router_to("analyst"))

    response = await chat_client.post(
        "/api/chat",
        json={"scope": "global", "message": "thoughts?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["agent_used"] == "analyst"
    assert "specific listing" in body["assistant_turn"]["content"].lower()


@pytest.mark.asyncio
async def test_listing_scope_404_for_unknown_listing(chat_client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Listing-scoped chat against a non-existent listing returns 404 before routing."""
    # Router shouldn't even be called, but pin it to operator just in case.
    import silvercurrent.api.chat as chat_module

    monkeypatch.setattr(chat_module, "RouterAgent", _force_router_to("operator"))

    response = await chat_client.post(
        "/api/chat",
        json={"scope": f"listing:{uuid4()}", "message": "Hi"},
    )

    assert response.status_code == 404
