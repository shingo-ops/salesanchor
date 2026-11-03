"""ADR-1058 秘1: 使用の記録の値の一覧と record_usage_isolated の試験（DB 不要）。"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest

from app.services import llm_budget
from app.services.llm_budget import (
    USAGE_ERROR_CODES,
    USAGE_OUTCOMES,
    USAGE_PURPOSES,
    USAGE_SDKS,
    UsageCounts,
    _outcome_columns,
    _usage_event_columns,
    record_usage_isolated,
)


def test_value_sets():
    assert USAGE_PURPOSES == {
        "line_extraction",
        "line_extraction_shadow",
        "inventory_parse_fallback",
        "translation_inbound",
        "translation_inbound_escalation",
        "translation_outbound",
        "secretary_intent",
    }
    assert USAGE_SDKS == {"google-genai", "google-generativeai", "codex-cli", "claude-code"}
    assert USAGE_ERROR_CODES == {
        "auth_failed",
        "timeout",
        "rate_limited",
        "http_error",
        "unreadable",
        "tool_used",
        "not_ready",
        "busy",
        "other",
    }
    assert USAGE_OUTCOMES == {"ok", "failed"}


@pytest.mark.parametrize(
    "outcome,error_code,expected",
    [
        ("ok", None, {"outcome": "ok", "error_code": None}),
        ("failed", "timeout", {"outcome": "failed", "error_code": "timeout"}),
    ],
)
def test_outcome_columns_valid(outcome, error_code, expected):
    assert _outcome_columns(outcome, error_code) == expected


@pytest.mark.parametrize(
    "outcome,error_code",
    [("ok", "timeout"), ("failed", None), ("failed", "nope"), ("maybe", None)],
)
def test_outcome_columns_invalid(outcome, error_code):
    with pytest.raises(ValueError):
        _outcome_columns(outcome, error_code)


@pytest.mark.parametrize("sdk", ["claude-code", "codex-cli"])
def test_usage_event_columns_accepts_cli_sdks(sdk):
    cols = _usage_event_columns(
        purpose="secretary_intent",
        model="sonnet",
        sdk=sdk,
        counts=UsageCounts(),
        tenant_id=1,
        extraction_attempt_id=None,
        extraction_shadow_run_id=None,
        discord_inbound_message_id=None,
        source_ref=None,
    )
    assert cols["cost_usd"] is None
    assert cols["prompt_tokens"] is None
    assert cols["total_tokens"] is None


def _fake_session_factory(session):
    @asynccontextmanager
    async def factory():
        yield session

    return factory


def _fake_session(execute_error: Exception | None = None):
    session = AsyncMock()
    if execute_error is not None:
        session.execute.side_effect = execute_error
    return session


def _call(**overrides):
    kwargs = dict(
        purpose="secretary_intent",
        model="sonnet",
        sdk="claude-code",
        counts=UsageCounts(),
        outcome="failed",
        error_code="auth_failed",
        tenant_id=1,
    )
    kwargs.update(overrides)
    return record_usage_isolated(**kwargs)


@pytest.mark.asyncio
async def test_isolated_writes_one_row_and_commits(monkeypatch):
    session = _fake_session()
    monkeypatch.setattr("app.database.AsyncSessionLocal", _fake_session_factory(session))
    await _call()
    assert session.execute.await_count == 1
    assert session.commit.await_count == 1
    args = session.execute.await_args.args
    assert "outcome" in str(args[0])
    params = args[1]
    assert params["outcome"] == "failed"
    assert params["error_code"] == "auth_failed"
    assert params["purpose"] == "secretary_intent"
    assert params["cost_usd"] is None


@pytest.mark.asyncio
async def test_isolated_swallows_execute_error(monkeypatch, caplog):
    session = _fake_session(execute_error=RuntimeError("boom"))
    monkeypatch.setattr("app.database.AsyncSessionLocal", _fake_session_factory(session))
    with caplog.at_level(logging.ERROR, logger=llm_budget.logger.name):
        await _call()
    assert session.commit.await_count == 0
    lines = [r.getMessage() for r in caplog.records if "使用の記録に書けませんでした" in r.getMessage()]
    assert len(lines) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "overrides",
    [
        {"outcome": "ok", "error_code": "timeout"},
        {"purpose": "nope"},
    ],
)
async def test_isolated_rejects_bad_values_without_writing(monkeypatch, overrides):
    session = _fake_session()
    monkeypatch.setattr("app.database.AsyncSessionLocal", _fake_session_factory(session))
    await _call(**overrides)
    assert session.execute.await_count == 0
    assert session.commit.await_count == 0
