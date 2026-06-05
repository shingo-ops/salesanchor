"""
ADR-SA-17: 双方向自動判定 + 2層辞書昇格フローの単体テスト。

カバー:
  - detect_inbound_target_language: 日本語→en / 非日本語(英・中)→ja（I-1）
  - _glossary_pair_for_target: target から辞書 pair 導出
  - translate_inbound: target に応じた glossary pair でロード（I-1/I-5）
  - propose_share / reject_promotion / approve_promotion（I-9: 匿名コピー・非破壊）
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import message_translator, translation_glossary
from app.services.llm_budget import BudgetStatus
from app.services.message_translator import (
    _glossary_pair_for_target,
    detect_inbound_target_language,
    translate_inbound,
)
from app.services.translation_glossary import (
    approve_promotion,
    propose_share,
    reject_promotion,
)

# ---------------------------------------------------------------------------
# 双方向自動判定（I-1）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("こんにちは、在庫はありますか？", "en"),   # ひらがな → 日本語 → en へ
        ("カードを5枚ください", "en"),              # カタカナ → 日本語 → en へ
        ("ｱｲｳｴｵ", "en"),                            # 半角カナ → 日本語 → en へ
        ("Do you have this card in stock?", "ja"),  # 英語 → ja へ
        ("你好，有现货吗？", "ja"),                  # 中国語（漢字のみ）→ 非日本語 → ja へ
        ("PSA 10 Charizard", "ja"),                 # 英数字のみ → ja へ
        ("", "ja"),                                 # 空 → ja
        ("   ", "ja"),                              # 空白のみ → ja
    ],
)
def test_detect_inbound_target_language(text: str, expected: str):
    assert detect_inbound_target_language(text) == expected


def test_glossary_pair_for_target():
    assert _glossary_pair_for_target("en") == "ja->en"
    assert _glossary_pair_for_target("ja") == "en->ja"
    # 未知 target は en->ja に倒す（非日本語集約）
    assert _glossary_pair_for_target("zh") == "en->ja"


@pytest.mark.asyncio
async def test_translate_inbound_uses_ja_en_pair_for_english_target():
    """target=en（原文が日本語）のとき glossary を ja->en でロードする（I-1/I-5）。"""
    db = AsyncMock()
    payload = json.dumps({
        "translated_text": "We have stock.",
        "confidence": 0.93,
        "original_language": "ja",
        "flagged_terms": [],
    })
    response = MagicMock()
    response.text = payload
    usage = MagicMock()
    usage.prompt_token_count = 10
    usage.candidates_token_count = 5
    response.usage_metadata = usage

    genai = MagicMock()
    model = MagicMock()
    model.generate_content_async = AsyncMock(return_value=response)
    genai.GenerativeModel = MagicMock(return_value=model)
    message_translator._GENAI_CACHE["module"] = genai

    try:
        with patch.object(
            message_translator, "_get_cached_translation",
            new_callable=AsyncMock, return_value=None,
        ), patch(
            "app.services.message_translator.load_glossary",
            new_callable=AsyncMock, return_value=[],
        ) as mock_load, patch(
            "app.services.message_translator.check_budget",
            new_callable=AsyncMock, return_value=BudgetStatus.UNDER,
        ), patch(
            "app.services.message_translator.record_cost", new_callable=AsyncMock,
        ), patch.object(
            message_translator, "_save_translation", new_callable=AsyncMock,
        ), patch(
            "app.services.message_translator._ensure_api_key", return_value="fake-key",
        ):
            await translate_inbound(
                db=db, tenant_id=1,
                table_ref="tenant_001.message_translations",
                message_id="mid_ja", message_text="在庫はあります。",
                target_language="en",
            )
    finally:
        message_translator._GENAI_CACHE.clear()

    # load_glossary が ja->en で呼ばれたこと
    assert mock_load.await_args.kwargs.get("language_pair") == "ja->en"


# ---------------------------------------------------------------------------
# 昇格フロー（I-9）
# ---------------------------------------------------------------------------


def _result_first(value):
    r = MagicMock()
    r.first.return_value = value
    return r


@pytest.mark.asyncio
async def test_propose_share_returns_true_when_updated():
    db = AsyncMock()
    db.execute.return_value = _result_first((42,))
    ok = await propose_share(db, entry_id=42, tenant_id=1)
    assert ok is True


@pytest.mark.asyncio
async def test_propose_share_returns_false_when_not_owned():
    db = AsyncMock()
    db.execute.return_value = _result_first(None)
    ok = await propose_share(db, entry_id=42, tenant_id=999)
    assert ok is False


@pytest.mark.asyncio
async def test_reject_promotion_returns_true_when_updated():
    db = AsyncMock()
    db.execute.return_value = _result_first((7,))
    assert await reject_promotion(db, entry_id=7) is True


@pytest.mark.asyncio
async def test_approve_promotion_anonymous_copy_and_non_destructive():
    """承認は共有へ匿名コピー（tenant_id NULL）し、私有エントリは残す（非破壊）。"""
    db = AsyncMock()
    # 1) 提案中の私有エントリ取得 2) 既存共有なし 3) INSERT shared 4) UPDATE private
    db.execute.side_effect = [
        _result_first(("Charizard", None, "en->ja", "product_name", None)),
        _result_first(None),
        _result_first(None),  # INSERT
        _result_first(None),  # UPDATE private approved
    ]

    ok = await approve_promotion(db, entry_id=10)
    assert ok is True

    sqls = [str(call.args[0]) for call in db.execute.call_args_list]
    # 共有コピーは tenant_id NULL（匿名・提供テナント非開示）で INSERT される
    assert any("INSERT INTO" in s and "VALUES (NULL," in s for s in sqls)
    # 私有エントリは DELETE されず approved に更新される（非破壊）
    assert any("share_status = 'approved'" in s for s in sqls)
    assert not any("DELETE FROM" in s for s in sqls)


@pytest.mark.asyncio
async def test_approve_promotion_not_found_is_idempotent():
    """提案中でない（既にレビュー済み等）なら False（冪等・自動昇格しない）。"""
    db = AsyncMock()
    db.execute.side_effect = [_result_first(None)]
    assert await approve_promotion(db, entry_id=10) is False


@pytest.mark.asyncio
async def test_approve_promotion_updates_existing_shared_entry():
    """同一語の共有エントリが既にあれば INSERT せず UPDATE（重複させない）。"""
    db = AsyncMock()
    db.execute.side_effect = [
        _result_first(("PSA 10", "PSA 10", "en->ja", "grade", None)),
        _result_first((55,)),   # 既存共有あり
        _result_first(None),    # UPDATE existing shared
        _result_first(None),    # UPDATE private approved
    ]
    ok = await approve_promotion(db, entry_id=11)
    assert ok is True
    sqls = [str(call.args[0]) for call in db.execute.call_args_list]
    assert not any("INSERT INTO" in s for s in sqls)


def test_promotion_queue_item_has_no_tenant_field():
    """匿名性: PromotionQueueItem は提供テナント（tenant_id）を持たない（I-9）。"""
    fields = set(translation_glossary.PromotionQueueItem.__dataclass_fields__.keys())
    assert "tenant_id" not in fields
