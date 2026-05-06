"""Tests for `compute_deal_metrics`, the Analyst agent, and `/api/analyze`.

The Anthropic client is mocked end-to-end (no live tokens). Tools that hit the
DB use the same in-memory SQLite session fixtures as the chat tests.
"""

from __future__ import annotations

import json
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
from silvercurrent.agents.tools.deal_metrics import (
    SBA_ANNUAL_RATE,
    SBA_DOWN_PAYMENT_FRACTION,
    SBA_TERM_YEARS,
    compute_deal_metrics,
)
from silvercurrent.db.models import Base, Listing
from silvercurrent.db.session import get_session
from silvercurrent.main import app

# --- Fixtures -----------------------------------------------------------------


_FTS5_DDL = """
CREATE VIRTUAL TABLE IF NOT EXISTS listing_document_chunk_fts USING fts5(
    document_id UNINDEXED,
    listing_id UNINDEXED,
    chunk_index UNINDEXED,
    page_hint UNINDEXED,
    content,
    tokenize='porter unicode61'
)
"""


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Per-test in-memory sqlite session."""
    from sqlalchemy import text

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text(_FTS5_DDL))
    factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as s:
        yield s
    await engine.dispose()


@pytest_asyncio.fixture
async def analyze_client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """An AsyncClient with the FastAPI app's session dep overridden."""

    async def _override() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_session] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c
    app.dependency_overrides.clear()


# --- Mock helpers -------------------------------------------------------------


def _text_response(text: str, *, input_tokens: int = 80, output_tokens: int = 40) -> MagicMock:
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
    block_id: str = "toolu_test",
) -> MagicMock:
    block = ToolUseBlock(type="tool_use", id=block_id, name=tool_name, input=tool_input)
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


def _seed_listing(session: AsyncSession, **overrides: Any) -> Listing:
    """Build and persist a Listing with sensible defaults that the test can override."""
    defaults: dict[str, Any] = {
        "business_name": "Acme HVAC",
        "industry": "HVAC services",
        "location": "Miami, FL",
        "asking_price": 1_200_000,
        "sde": 350_000,
        "revenue": 2_100_000,
        "narrative": "Established HVAC contractor with 12 years of operations.",
        "reason_for_selling": "Owner retiring.",
        "broker_name": "Sunbelt Business Brokers",
    }
    defaults.update(overrides)
    listing = Listing(**defaults)
    session.add(listing)
    return listing


# --- compute_deal_metrics -----------------------------------------------------


@pytest.mark.asyncio
async def test_compute_deal_metrics_full_disclosure(db_session: AsyncSession) -> None:
    """Listing with asking, SDE, and revenue all set yields all derived metrics."""
    listing = _seed_listing(db_session)
    await db_session.commit()

    env = await compute_deal_metrics(listing_id=listing.id, session=db_session)

    assert env.ok
    data = env.data
    assert data["inputs"] == {"asking_price": 1_200_000, "sde": 350_000, "revenue": 2_100_000}
    assert data["multiples"]["asking_multiple_sde"] == round(1_200_000 / 350_000, 2)
    assert data["multiples"]["asking_multiple_revenue"] == round(1_200_000 / 2_100_000, 2)
    assert data["sde_margin"] == round(350_000 / 2_100_000, 4)
    assert data["missing_fields"] == []

    sba = data["sba_scenario"]
    assert sba["assumptions"]["down_payment_fraction"] == SBA_DOWN_PAYMENT_FRACTION
    assert sba["assumptions"]["annual_rate"] == SBA_ANNUAL_RATE
    assert sba["assumptions"]["term_years"] == SBA_TERM_YEARS
    assert sba["down_payment"] == round(1_200_000 * SBA_DOWN_PAYMENT_FRACTION)
    assert sba["loan_amount"] == 1_200_000 - sba["down_payment"]
    assert sba["annual_debt_service"] > 0
    assert sba["dscr"] == round(350_000 / sba["annual_debt_service"], 2)
    assert sba["sde_after_debt_service"] == round(350_000 - sba["annual_debt_service"])


@pytest.mark.asyncio
async def test_compute_deal_metrics_reports_missing_fields(db_session: AsyncSession) -> None:
    """Missing financials show up in `missing_fields` and the affected metrics are omitted."""
    listing = _seed_listing(db_session, sde=None, revenue=None)
    await db_session.commit()

    env = await compute_deal_metrics(listing_id=listing.id, session=db_session)

    assert env.ok
    data = env.data
    assert "sde" in data["missing_fields"]
    assert "revenue" in data["missing_fields"]
    assert "asking_multiple_sde" not in data["multiples"]
    assert "asking_multiple_revenue" not in data["multiples"]
    assert data["sde_margin"] is None
    # SBA scenario can still compute from asking alone, but DSCR requires SDE.
    assert data["sba_scenario"] is not None
    assert "dscr" not in data["sba_scenario"]


@pytest.mark.asyncio
async def test_compute_deal_metrics_listing_not_found(db_session: AsyncSession) -> None:
    """Non-existent listing returns a fail envelope, not an exception."""
    env = await compute_deal_metrics(listing_id=uuid4(), session=db_session)
    assert not env.ok
    assert "not found" in (env.error or "")


@pytest.mark.asyncio
async def test_compute_deal_metrics_amortization_sanity() -> None:
    """Hand-check the SBA debt-service number against a known-good amortization.

    For a $900k loan at 10.5% APR, 10y term, the monthly payment is ~$12,141
    and the annual debt service is ~$145,694. We allow a small rounding band.
    """
    from silvercurrent.agents.tools.deal_metrics import _annual_debt_service

    annual = _annual_debt_service(loan_amount=900_000, annual_rate=0.105, term_years=10)
    # Independent reference value computed offline.
    assert 145_000 < annual < 146_500


# --- AnalystAgent unit tests --------------------------------------------------


@pytest.mark.asyncio
async def test_analyst_runs_three_tools_then_writes_deal_sheet(db_session: AsyncSession) -> None:
    """Happy path: model calls all three tools across iterations, then produces the Deal Sheet."""
    listing = _seed_listing(db_session)
    await db_session.commit()

    fake_client = _client_with_responses(
        _tool_use_response("get_active_listing", {}, block_id="t1"),
        _tool_use_response("get_user_criteria", {}, block_id="t2"),
        _tool_use_response("compute_deal_metrics", {}, block_id="t3"),
        _text_response("### Snapshot\nAcme HVAC...", output_tokens=200),
    )

    agent = AnalystAgent(client=fake_client, session=db_session, model="test-model")
    result = await agent.analyze(listing_id=listing.id)

    assert "Snapshot" in result.deal_sheet
    assert result.iterations == 4
    assert result.usage.model == "test-model"
    # Four messages.create calls were made.
    assert fake_client.messages.create.call_count == 4


@pytest.mark.asyncio
async def test_analyst_surfaces_tool_failure(db_session: AsyncSession) -> None:
    """When `compute_deal_metrics` fails (e.g. listing missing), the model gets is_error and recovers."""
    listing = _seed_listing(db_session)
    await db_session.commit()

    # Sequence: model asks for metrics on a wrong id (we'll force the failure by deleting),
    # gets is_error, then writes a Deal Sheet that acknowledges the gap.
    fake_client = _client_with_responses(
        _tool_use_response("compute_deal_metrics", {}, block_id="t1"),
        _text_response("### Snapshot\n... metrics unavailable.", output_tokens=80),
    )

    # Wipe the listing so the tool fails.
    await db_session.delete(listing)
    await db_session.commit()

    agent = AnalystAgent(client=fake_client, session=db_session, model="test-model")
    result = await agent.analyze(listing_id=listing.id)

    assert "metrics unavailable" in result.deal_sheet
    second_call = fake_client.messages.create.call_args_list[1]
    sent_messages = second_call.kwargs["messages"]
    tool_result_block = sent_messages[-1]["content"][0]
    assert tool_result_block["is_error"] is True
    payload = json.loads(tool_result_block["content"])
    assert "not found" in payload["error"]


@pytest.mark.asyncio
async def test_analyst_invokes_score_against_criteria(db_session: AsyncSession) -> None:
    """The new `score_against_criteria` tool is wired into the loop and its output flows back."""
    listing = _seed_listing(db_session)
    await db_session.commit()

    fake_client = _client_with_responses(
        _tool_use_response("score_against_criteria", {}, block_id="t1"),
        _text_response("### Hard knockouts\n- Declining revenue 3 years running. — PASS"),
    )

    agent = AnalystAgent(client=fake_client, session=db_session, model="test-model")
    result = await agent.analyze(listing_id=listing.id)

    # Second messages.create call's payload includes the tool result for score_against_criteria.
    second_call = fake_client.messages.create.call_args_list[1]
    sent_messages = second_call.kwargs["messages"]
    tool_result_block = sent_messages[-1]["content"][0]
    assert tool_result_block.get("is_error") is not True
    payload = json.loads(tool_result_block["content"])
    assert "fit_result" in payload
    fit = payload["fit_result"]
    assert fit["band"] in {"strong", "partial", "weak", "mismatch", "unknown"}
    assert "PASS" in result.deal_sheet


@pytest.mark.asyncio
async def test_analyst_caps_iterations(db_session: AsyncSession) -> None:
    """If the model never stops calling tools, analyze() returns a bounded fallback."""
    listing = _seed_listing(db_session)
    await db_session.commit()

    fake_client = MagicMock()
    fake_client.messages = MagicMock()
    fake_client.messages.create = AsyncMock(return_value=_tool_use_response("get_active_listing", {}, block_id="loop"))

    agent = AnalystAgent(client=fake_client, session=db_session, model="test-model")
    result = await agent.analyze(listing_id=listing.id)

    assert "could not converge" in result.deal_sheet
    assert result.iterations == 6  # MAX_ITERATIONS


# --- /api/analyze endpoint tests ----------------------------------------------


@pytest.mark.asyncio
async def test_analyze_endpoint_persists_deal_sheet(
    analyze_client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A successful POST persists a DealSheet row and returns it serialized."""
    listing = _seed_listing(db_session)
    await db_session.commit()

    fake_client = _client_with_responses(_text_response("### Snapshot\nAcme HVAC", output_tokens=120))

    import silvercurrent.api.analyze as analyze_module

    real_agent = analyze_module.AnalystAgent  # type: ignore[attr-defined]

    def mock_agent(**kwargs: Any) -> Any:
        return real_agent(client=fake_client, session=kwargs.get("session"), model="test-model")

    monkeypatch.setattr(analyze_module, "AnalystAgent", mock_agent)

    response = await analyze_client.post(f"/api/analyze/{listing.id}")

    assert response.status_code == 200
    body = response.json()
    assert "Snapshot" in body["deal_sheet"]["markdown"]
    assert body["deal_sheet"]["listing_id"] == str(listing.id)
    assert body["deal_sheet"]["model"] == "test-model"
    assert body["deal_sheet"]["iterations"] == 1
    assert body["deal_sheet"]["output_tokens"] == 120
    assert body["usage"]["model"] == "test-model"
    # Row should now be retrievable via GET.
    history_response = await analyze_client.get(f"/api/analyze/{listing.id}")
    assert history_response.status_code == 200
    rows = history_response.json()
    assert len(rows) == 1
    assert rows[0]["id"] == body["deal_sheet"]["id"]


@pytest.mark.asyncio
async def test_analyze_endpoint_404_for_unknown_listing(analyze_client: AsyncClient) -> None:
    """Unknown listing id returns 404 before invoking the agent."""
    response = await analyze_client.post(f"/api/analyze/{uuid4()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_deal_sheets_returns_newest_first(
    analyze_client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Multiple analyses for one listing come back newest-first."""
    from datetime import UTC, datetime, timedelta

    from silvercurrent.db.models import DealSheet

    listing = _seed_listing(db_session)
    await db_session.commit()

    base = datetime.now(UTC)
    older = DealSheet(
        listing_id=listing.id,
        markdown="### Snapshot\nfirst run",
        model="test-model",
        input_tokens=100,
        output_tokens=50,
        iterations=1,
        created_at=base,
    )
    newer = DealSheet(
        listing_id=listing.id,
        markdown="### Snapshot\nsecond run",
        model="test-model",
        input_tokens=120,
        output_tokens=60,
        iterations=2,
        created_at=base + timedelta(seconds=5),
    )
    db_session.add(older)
    db_session.add(newer)
    await db_session.commit()

    response = await analyze_client.get(f"/api/analyze/{listing.id}")
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 2
    assert "second run" in rows[0]["markdown"]
    assert "first run" in rows[1]["markdown"]


@pytest.mark.asyncio
async def test_list_deal_sheets_404_for_unknown_listing(analyze_client: AsyncClient) -> None:
    """GET on a non-existent listing returns 404."""
    response = await analyze_client.get(f"/api/analyze/{uuid4()}")
    assert response.status_code == 404
