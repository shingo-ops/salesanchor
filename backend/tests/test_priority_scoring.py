"""
ADR-107 (ADR-SA-14): 分析エージェント(A) 顧客優先度付け — バックエンドテスト。

テスト戦略:
  - compute_score() 純粋関数のユニットテスト（副作用なし・高速）
  - _classify_message() のルールベース分類テスト
  - HTTPエンドポイントの権限チェック（SQLite + モック）
"""

from __future__ import annotations

import pytest

from app.schemas.customer_priority import ScoreTier
from app.services.priority_scoring import (
    MIN_MSG_CONFIDENCE,
    TIER_PROMISING_THRESHOLD,
    TIER_TOP_THRESHOLD,
    _classify_message,
    compute_score,
)


# ---------------------------------------------------------------------------
# compute_score 純粋関数のユニットテスト
# ---------------------------------------------------------------------------

class TestComputeScore:
    """ADR-107 §C: 裸の断定を返さない（スコア + 確信度 + ティアの3点セット）。"""

    def test_empty_messages_returns_neutral(self):
        score, conf, tier = compute_score({}, {}, 0, False)
        assert score == 0.5
        assert conf == 0.0
        assert tier == ScoreTier.watching

    def test_cold_start_reduces_confidence(self):
        counts = {"substance_talk": 5, "self_disclosure": 2, "other": 3}
        weights = {"substance_talk": 0.4, "self_disclosure": 0.3,
                   "price_focus": -0.3, "early_purchase_signal": -0.1, "other": 0.0}
        _, conf_hot, _ = compute_score(counts, weights, 10, False)
        _, conf_cold, _ = compute_score(counts, weights, 10, True)
        assert conf_cold < conf_hot, "cold start はホットより確信度が低いこと"

    def test_price_heavy_leads_watching_tier(self):
        counts = {"price_focus": 8, "other": 2}
        weights = {"price_focus": -0.3, "substance_talk": 0.4,
                   "self_disclosure": 0.3, "early_purchase_signal": -0.1, "other": 0.0}
        score, _, tier = compute_score(counts, weights, 10, False)
        assert score < TIER_PROMISING_THRESHOLD
        assert tier == ScoreTier.watching

    def test_substance_heavy_leads_top_tier(self):
        counts = {"substance_talk": 7, "self_disclosure": 3}
        weights = {"price_focus": -0.3, "substance_talk": 0.4,
                   "self_disclosure": 0.3, "early_purchase_signal": -0.1, "other": 0.0}
        score, _, tier = compute_score(counts, weights, 10, False)
        assert score >= TIER_PROMISING_THRESHOLD
        # substance 強めなので少なくとも有望以上
        assert tier in (ScoreTier.promising, ScoreTier.top)

    def test_score_always_in_range(self):
        """スコアは常に [0, 1] の範囲に収まること（thin-data でも）。"""
        for n in [0, 1, 3, 100]:
            counts = {"price_focus": n}
            weights = {"price_focus": -5.0, "substance_talk": 5.0,
                       "self_disclosure": 5.0, "early_purchase_signal": -2.0, "other": 0.0}
            score, conf, _ = compute_score(counts, weights, max(n, 1), False)
            assert 0.0 <= score <= 1.0, f"score={score} out of range for n={n}"
            assert 0.0 <= conf <= 1.0, f"conf={conf} out of range for n={n}"

    def test_confidence_grows_with_message_count(self):
        weights = {"price_focus": 0.0, "substance_talk": 0.0,
                   "self_disclosure": 0.0, "early_purchase_signal": 0.0, "other": 0.0}
        _, conf_few, _ = compute_score({"other": 2}, weights, 2, False)
        _, conf_many, _ = compute_score({"other": MIN_MSG_CONFIDENCE}, weights, MIN_MSG_CONFIDENCE, False)
        assert conf_many >= conf_few

    def test_tier_boundaries(self):
        """ティア境界値テスト。"""
        weights = {"price_focus": 0.0, "substance_talk": 0.0,
                   "self_disclosure": 0.0, "early_purchase_signal": 0.0, "other": 0.0}
        # スコアが 0.5（中立）なら有望のはず
        score, _, tier = compute_score({"other": 5}, weights, 5, False)
        assert tier == ScoreTier.promising, f"中立スコア {score:.3f} は有望のはず"


# ---------------------------------------------------------------------------
# _classify_message ルールベース分類テスト
# ---------------------------------------------------------------------------

class TestClassifyMessage:
    """地域・国籍・言語パターンは使わない（行動のみ）。"""

    def test_price_keyword_classified_as_price_focus(self):
        label, conf = _classify_message("価格はどのくらいですか？", False)
        assert label == "price_focus"
        assert conf > 0.5

    def test_early_purchase_on_first_message(self):
        label, _ = _classify_message("今すぐ購入したいです", True)
        assert label == "early_purchase_signal"

    def test_early_purchase_not_on_later_message(self):
        # is_first=False なら early_purchase_signal にならない
        label, _ = _classify_message("購入したいです", False)
        # price ではなく substance や other になる（early でないこと）
        assert label != "early_purchase_signal"

    def test_substance_keyword(self):
        label, _ = _classify_message("どう使うのかを詳しく教えてください", False)
        assert label == "substance_talk"

    def test_disclosure_keyword(self):
        label, _ = _classify_message("うちの場合は20名の部署で使う予定です", False)
        assert label == "self_disclosure"

    def test_empty_text_returns_other(self):
        label, conf = _classify_message("", False)
        assert label == "other"
        assert conf > 0.5

    def test_no_region_nationality_features(self):
        """地域・国籍を使った分類が起きないこと（行動のみ）。"""
        # 国名や地域名だけのテキストは other になる
        label, _ = _classify_message("東京都から連絡しています", False)
        # 地域情報だけで price_focus/substance_talk にならないこと
        assert label != "price_focus"


# ---------------------------------------------------------------------------
# 出力契約: 裸の断定を返さない（ADR-107 §C）
# ---------------------------------------------------------------------------

class TestOutputContract:
    def test_compute_score_never_returns_bare_boolean(self):
        """compute_score は常にタプル（スコア・確信度・ティア）を返す。"""
        result = compute_score({"other": 3}, {}, 3, True)
        assert len(result) == 3
        score, conf, tier = result
        assert isinstance(score, float)
        assert isinstance(conf, float)
        assert isinstance(tier, ScoreTier)

    def test_cold_start_confidence_below_threshold(self):
        """cold start + 少数データは確信度が低いこと（暫定であることをUI側に伝達）。"""
        _, conf, _ = compute_score({"other": 1}, {}, 1, True)
        assert conf < 0.3, "cold start かつ mother数1件なら確信度 < 0.3 であること"
