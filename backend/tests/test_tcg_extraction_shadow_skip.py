"""ルールのない仕入元では試運転（run_shadow_for_job）を呼ばない（設計 追補2 §6）。"""
from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest

import app.tasks.tcg_extraction as task

_FULL_RULE = {
    "extraction_price_format": "円",
    "extraction_qty_format": "在庫",
    "extraction_order_pattern": '["price","@","quantity"]',
}


def _run(monkeypatch, supplier_context, *, shadow_enabled="1"):
    monkeypatch.setenv("EXTRACTION_SHADOW_ENABLED", shadow_enabled)
    monkeypatch.delenv("TCG_AUTO_ANALYZE", raising=False)
    shadow = MagicMock()
    monkeypatch.setattr(task, "run_shadow_for_job", shadow)
    monkeypatch.setattr(
        task, "extract_message",
        lambda *a, **kw: {"status": "done", "items": [], "prompt_version": "v", "error_message": None},
    )
    monkeypatch.setattr(task, "load_work_reference", lambda s, schema: {})
    monkeypatch.setattr(task, "reference_digest", lambda ref: "d")
    recorder = MagicMock()
    recorder.prepare_items.return_value = []
    task._run_recorded_extraction(
        MagicMock(), "ej-1", "raw", {}, recorder,
        supplier_context=supplier_context, knowledge_links=None, supplier_id=42,
    )
    return shadow


@pytest.mark.parametrize("context", [None, {}, {**_FULL_RULE, "extraction_order_pattern": ""}])
def test_shadow_not_called_without_supplier_rule(monkeypatch, caplog, context):
    with caplog.at_level(logging.INFO, logger="app.tasks.tcg_extraction"):
        shadow = _run(monkeypatch, context)
    shadow.assert_not_called()
    assert "shadow skipped: no supplier rule supplier_id=42 ej=ej-1" in caplog.text


def test_shadow_called_with_supplier_rule(monkeypatch):
    shadow = _run(monkeypatch, _FULL_RULE)
    shadow.assert_called_once()


def test_shadow_not_called_when_disabled(monkeypatch):
    shadow = _run(monkeypatch, _FULL_RULE, shadow_enabled="0")
    shadow.assert_not_called()
