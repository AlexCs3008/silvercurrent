"""Tests for the Operator agent's tool-loop and the `/api/chat` endpoint.

The Anthropic client is mocked end-to-end (no live tokens). Knowledge-base
search is mocked at the function level so we don't need a populated Chroma.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from anthropic.types import TextBlock, ToolUseBlock
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from silvercurrent.agents.operator import OperatorAgent
from silvercurrent.agents.tools._envelope import fail, ok
from silvercurrent.db.models import Base, ChatTurn
from silvercurrent.db.session import get_session
from silvercurrent.main import app

# --- Mock helpers -------------------------------------------------------------


def _text_response(text: str, *, input_tokens: int = 80, output_tokens: int = 40) -> MagicMock:
    """Build a final, no-tool-call response."""
    block = TextBlock(type="text", text=text, citations=None)
    response = MagicMock()
    response.content = [block]
    response.stop_reason = "end_turn"
    response.usage = MagicMock(input_tokens=input_tokens, output_tokens=output_tokens)
    return response


def _tool_use_response(
    tool_name: str,
    tool_input: dict[str, Any],
    *,
    input_tokens: int = 100,
    output_tokens: int = 50,
) -> MagicMock:
    """Build a response that asks for one tool call and nothing else."""
    block = ToolUseBlock(type="tool_use", id="toolu_test", name=tool_name, input=tool_input)
    response = MagicMock()
    response.content = [block]
    response.stop_reason = "tool_use"
    response.usage = MagicMock(input_tokens=input_tokens, output_tokens=output_tokens)
    return response


def _client_with_responses(*responses: MagicMock) -> MagicMock:
    """Return an AsyncAnthropic-shaped mock that yields each response in sequence."""
    client = MagicMock()
    client.messages = MagicMock()
    client.messages.create = AsyncMock(side_effect=list(responses))
    return client


# --- OperatorAgent unit tests -------------------------------------------------


@pytest.mark.asyncio
async def test_operator_returns_text_when_model_replies_directly() -> None:
    """If the model produces a text-only response on iteration 1, run() returns it."""
    fake_client = _client_with_responses(_text_response("Direct answer here."))
    agent = OperatorAgent(client=fake_client, model="test-model")

    result = await agent.run(user_message="hi", history=[])

    assert result.content == "Direct answer here."
    assert result.iterations == 1
    assert result.usage.input_tokens == 80
    assert result.usage.output_tokens == 40
    assert result.usage.model == "test-model"


@pytest.mark.asyncio
async def test_operator_executes_kb_search_then_answers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tool-use round-trip: model asks for `search_knowledge_base`, gets passages, answers."""
    fake_client = _client_with_responses(
        _tool_use_response("search_knowledge_base", {"query": "SBA loans"}, output_tokens=20),
        _text_response("SBA 7(a) caps at $5M [sba_loans.md].", output_tokens=60),
    )

    async def fake_kb_search(query: str, k: int = 5) -> Any:
        return ok(
            {
                "query": query,
                "k": k,
                "passages": [
                    {
                        "text": "SBA 7(a) caps at $5M.",
                        "source": "sba_loans.md",
                        "chunk_index": 0,
                        "total_chunks": 2,
                        "cosine_distance": 0.3,
                    }
                ],
            }
        )

    import silvercurrent.agents.operator as op_module

    monkeypatch.setattr(op_module, "search_knowledge_base", fake_kb_search)

    agent = OperatorAgent(client=fake_client, model="test-model")
    result = await agent.run(user_message="how do SBA loans work?", history=[])

    assert "SBA 7(a)" in result.content
    assert result.iterations == 2
    # Usage accumulates across both round trips.
    assert result.usage.output_tokens == 20 + 60


@pytest.mark.asyncio
async def test_operator_tool_failure_is_surfaced_to_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """When a tool returns a fail Envelope, the model gets `is_error: true` and can recover."""
    fake_client = _client_with_responses(
        _tool_use_response("search_knowledge_base", {"query": "x"}),
        _text_response("KB unavailable, but generally..."),
    )

    async def fake_kb_search(query: str, k: int = 5) -> Any:
        return fail("Operator collection is empty.")

    import silvercurrent.agents.operator as op_module

    monkeypatch.setattr(op_module, "search_knowledge_base", fake_kb_search)

    agent = OperatorAgent(client=fake_client, model="test-model")
    result = await agent.run(user_message="x", history=[])

    assert "KB unavailable" in result.content
    # Inspect what was sent to the model after the failed tool call.
    second_call = fake_client.messages.create.call_args_list[1]
    sent_messages = second_call.kwargs["messages"]
    tool_result_block = sent_messages[-1]["content"][0]
    assert tool_result_block["is_error"] is True
    assert "empty" in tool_result_block["content"]


@pytest.mark.asyncio
async def test_operator_passes_retrieved_passages_through_listing_source_wrapper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """KB results are wrapped in `<retrieved_passage>` tags before reaching the model (ADR 0002)."""
    fake_client = _client_with_responses(
        _tool_use_response("search_knowledge_base", {"query": "test"}),
        _text_response("ok"),
    )

    async def fake_kb_search(query: str, k: int = 5) -> Any:
        return ok(
            {
                "query": query,
                "k": k,
                "passages": [
                    {
                        "text": "Some retrieved content.",
                        "source": "doc.md",
                        "chunk_index": 0,
                        "total_chunks": 1,
                        "cosine_distance": 0.5,
                    }
                ],
            }
        )

    import silvercurrent.agents.operator as op_module

    monkeypatch.setattr(op_module, "search_knowledge_base", fake_kb_search)

    agent = OperatorAgent(client=fake_client, model="test-model")
    await agent.run(user_message="test", history=[])

    # The second call to messages.create should include a tool_result block whose
    # content has been wrapped in <retrieved_passage> tags.
    second_call = fake_client.messages.create.call_args_list[1]
    sent_messages = second_call.kwargs["messages"]
    tool_result_content = sent_messages[-1]["content"][0]["content"]
    assert "<retrieved_passage" in tool_result_content
    assert 'source="doc.md"' in tool_result_content
    assert "</retrieved_passage>" in tool_result_content


@pytest.mark.asyncio
async def test_operator_includes_history_in_prompt() -> None:
    """Prior `ChatTurn` rows are formatted as messages and prepended to the new user turn."""
    fake_client = _client_with_responses(_text_response("ok"))
    agent = OperatorAgent(client=fake_client, model="test-model")

    history = [
        ChatTurn(scope="global", role="user", content="earlier user message"),
        ChatTurn(scope="global", role="assistant", content="earlier assistant reply"),
    ]
    await agent.run(user_message="new message", history=history)

    call = fake_client.messages.create.call_args
    sent = call.kwargs["messages"]
    assert sent[0] == {"role": "user", "content": "earlier user message"}
    assert sent[1] == {"role": "assistant", "content": "earlier assistant reply"}
    assert sent[2] == {"role": "user", "content": "new message"}


@pytest.mark.asyncio
async def test_operator_caps_iterations(monkeypatch: pytest.MonkeyPatch) -> None:
    """When the model never stops calling tools, run() returns a bounded fallback."""
    # Always reply with another tool call.
    fake_client = MagicMock()
    fake_client.messages = MagicMock()
    fake_client.messages.create = AsyncMock(return_value=_tool_use_response("search_knowledge_base", {"query": "loop"}))

    async def fake_kb_search(query: str, k: int = 5) -> Any:
        return ok({"query": query, "k": k, "passages": []})

    import silvercurrent.agents.operator as op_module

    monkeypatch.setattr(op_module, "search_knowledge_base", fake_kb_search)

    agent = OperatorAgent(client=fake_client, model="test-model")
    result = await agent.run(user_message="x", history=[])

    assert "without converging" in result.content
    assert result.iterations == 5  # MAX_ITERATIONS


# --- /api/chat endpoint tests -------------------------------------------------


@pytest_asyncio.fixture
async def chat_session() -> AsyncIterator[AsyncSession]:
    """Per-test in-memory sqlite session for chat endpoint tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as s:
        yield s
    await engine.dispose()


@pytest_asyncio.fixture
async def chat_client(chat_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """An AsyncClient with the FastAPI app's session dep overridden for this test."""

    async def _override() -> AsyncIterator[AsyncSession]:
        yield chat_session

    app.dependency_overrides[get_session] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_chat_endpoint_persists_both_turns(chat_client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """A successful POST /api/chat persists user + assistant turns and returns both."""
    fake_client = _client_with_responses(_text_response("Hi back."))

    import silvercurrent.api.chat as chat_module

    real_operator_agent = chat_module.OperatorAgent  # type: ignore[attr-defined]

    def mock_agent(**kwargs: Any) -> Any:
        return real_operator_agent(client=fake_client, session=kwargs.get("session"), model="test-model")

    monkeypatch.setattr(chat_module, "OperatorAgent", mock_agent)

    response = await chat_client.post(
        "/api/chat",
        json={"scope": "global", "message": "Hello"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["user_turn"]["content"] == "Hello"
    assert body["assistant_turn"]["content"] == "Hi back."
    assert body["usage"]["model"] == "test-model"
    assert body["usage"]["iterations"] == 1

    # Both turns should now be retrievable via GET.
    list_response = await chat_client.get("/api/chat?scope=global")
    assert list_response.status_code == 200
    turns = list_response.json()
    assert len(turns) == 2
    assert turns[0]["role"] == "user"
    assert turns[1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_chat_endpoint_rejects_nonglobal_scope(chat_client: AsyncClient) -> None:
    """Phase 2 only supports scope='global'."""
    response = await chat_client.post(
        "/api/chat",
        json={"scope": "listing:abc", "message": "Hi"},
    )
    assert response.status_code == 400
    assert "global" in response.json()["detail"]


@pytest.mark.asyncio
async def test_chat_endpoint_validates_required_fields(chat_client: AsyncClient) -> None:
    """Empty message → 422."""
    response = await chat_client.post("/api/chat", json={"scope": "global", "message": ""})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_endpoint_loads_existing_history(
    chat_client: AsyncClient, chat_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Existing turns are passed back to the agent as history."""
    # Seed the DB with two prior turns with explicit, ordered timestamps so the
    # DESC-then-reverse history fetch isn't ambiguous.
    from datetime import UTC, datetime, timedelta

    base = datetime.now(UTC)
    chat_session.add(
        ChatTurn(
            scope="global",
            role="user",
            content="earlier",
            created_at=base,
        )
    )
    chat_session.add(
        ChatTurn(
            scope="global",
            role="assistant",
            content="earlier reply",
            created_at=base + timedelta(seconds=1),
        )
    )
    await chat_session.commit()

    fake_client = _client_with_responses(_text_response("new reply"))
    import silvercurrent.api.chat as chat_module

    real_operator_agent = chat_module.OperatorAgent  # type: ignore[attr-defined]

    def mock_agent(**kwargs: Any) -> Any:
        return real_operator_agent(client=fake_client, session=kwargs.get("session"), model="test-model")

    monkeypatch.setattr(chat_module, "OperatorAgent", mock_agent)

    response = await chat_client.post("/api/chat", json={"scope": "global", "message": "follow-up"})
    assert response.status_code == 200

    # Inspect the messages sent to Anthropic.
    sent = fake_client.messages.create.call_args.kwargs["messages"]
    assert sent[0]["content"] == "earlier"
    assert sent[1]["content"] == "earlier reply"
    assert sent[2]["content"] == "follow-up"


@pytest.mark.asyncio
async def test_chat_get_empty_scope_returns_empty_list(chat_client: AsyncClient) -> None:
    """GET /api/chat returns [] when nothing has been persisted."""
    response = await chat_client.get("/api/chat?scope=global")
    assert response.status_code == 200
    assert response.json() == []
