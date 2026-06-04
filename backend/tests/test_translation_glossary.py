"""
ADR-110: 翻訳グロッサリサービスの単体テスト。

カバー:
  - load_glossary: テナント固有 + グローバル共有のマージ（テナント優先）
  - format_glossary_for_prompt: グロッサリ注入テキストの生成
  - build_glossary_instructions: 訳す / 訳さない の指示生成
  - グロッサリ登録語を勝手に直訳しない（受け入れ条件 2）
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.translation_glossary import (
    GlossaryEntry,
    build_glossary_instructions,
    format_glossary_for_prompt,
    load_glossary,
)


def _make_entry(
    id: int,
    source_term: str,
    target_text: str | None,
    tenant_id: int | None = None,
    language_pair: str = "en->ja",
    term_type: str = "general",
) -> GlossaryEntry:
    return GlossaryEntry(
        id=id,
        tenant_id=tenant_id,
        source_term=source_term,
        target_text=target_text,
        language_pair=language_pair,
        term_type=term_type,
        is_active=True,
        source_ref=None,
        notes=None,
    )


# ---------------------------------------------------------------------------
# build_glossary_instructions
# ---------------------------------------------------------------------------


def test_build_instructions_with_target_text():
    """target_text があれば「→ 訳語と翻訳すること」指示を生成。"""
    entry = _make_entry(1, "PSA 10", "PSA 10（訳さない）")
    instructions = build_glossary_instructions([entry])
    assert len(instructions) == 1
    assert "PSA 10" in instructions[0].instruction
    assert "PSA 10（訳さない）" in instructions[0].instruction


def test_build_instructions_no_translate():
    """target_text が None なら「訳さない（原語保持）」指示を生成。"""
    entry = _make_entry(1, "Charizard", None)
    instructions = build_glossary_instructions([entry])
    assert len(instructions) == 1
    assert "Charizard" in instructions[0].instruction
    assert "保持" in instructions[0].instruction or "訳さない" in instructions[0].instruction


def test_build_instructions_multiple():
    entries = [
        _make_entry(1, "PSA 10", None, term_type="grade"),
        _make_entry(2, "BGS", None, term_type="grade"),
        _make_entry(3, "TCG", "トレーディングカードゲーム"),
    ]
    instructions = build_glossary_instructions(entries)
    assert len(instructions) == 3


# ---------------------------------------------------------------------------
# format_glossary_for_prompt
# ---------------------------------------------------------------------------


def test_format_empty_returns_empty_string():
    assert format_glossary_for_prompt([]) == ""


def test_format_includes_header():
    entry = _make_entry(1, "PSA", None)
    text = format_glossary_for_prompt([entry])
    assert "用語対応表" in text or "必須" in text
    assert "PSA" in text


def test_format_includes_do_not_translate_marker():
    entry = _make_entry(1, "Charizard", None, term_type="product_name")
    text = format_glossary_for_prompt([entry])
    assert "Charizard" in text
    # 「訳さない」または「保持」の指示が入っていること（ADR-110 受け入れ条件 2）
    assert "訳さない" in text or "保持" in text


# ---------------------------------------------------------------------------
# load_glossary（モック DB）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_load_glossary_tenant_overrides_global():
    """テナント固有エントリがグローバルより優先される（受け入れ条件 2）。"""
    db = AsyncMock()

    row_global = (1, None, "PSA", "グレード会社", "en->ja", "brand", True, None, None)
    row_tenant = (2, 1, "PSA", "PSA（訳さない）", "en->ja", "grade", True, None, None)

    mock_result = MagicMock()
    mock_result.fetchall.return_value = [row_global, row_tenant]
    db.execute.return_value = mock_result

    entries = await load_glossary(db, tenant_id=1, language_pair="en->ja")

    # 同一 source_term では tenant 側 (id=2) が残る
    assert len(entries) == 1
    assert entries[0].id == 2
    assert entries[0].tenant_id == 1


@pytest.mark.asyncio
async def test_load_glossary_global_used_if_no_tenant_entry():
    """テナント固有エントリがなければグローバルを使用。"""
    row_global = (1, None, "TCG", "トレーディングカードゲーム", "en->ja", "abbreviation", True, None, None)
    db = AsyncMock()

    mock_result = MagicMock()
    mock_result.fetchall.return_value = [row_global]
    db.execute.return_value = mock_result

    entries = await load_glossary(db, tenant_id=99, language_pair="en->ja")

    assert len(entries) == 1
    assert entries[0].tenant_id is None
    assert entries[0].source_term == "TCG"
