"""
ADR-107 (ADR-SA-14): 分析エージェント(A) 顧客優先度付け — スコア計算サービス。

信頼保護の不変条件 (§13):
  - 地域・国籍を特徴量に使わない（行動のみ）
  - thin-data で断定しない（確信度・母数必須）
  - テナント越境参照禁止（RLS + search_path で保護済み）
  - スコアは助言であり決定しない（低スコアで客を切る処理なし）
"""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.customer_priority import (
    CustomerScoreResponse,
    ScoreTier,
    SignalSummary,
)

logger = logging.getLogger(__name__)

# --- 閾値定数 ---
MIN_CALIBRATION_SAMPLES = 10  # テナント較正に必要な最小成約/失注件数
MIN_MESSAGES_FOR_SCORE = 3    # スコア計算に必要な最小メッセージ数
MIN_MSG_CONFIDENCE = 5        # 確信度「中」に必要なメッセージ数（以上で1.0）

# ティア境界
TIER_TOP_THRESHOLD = 0.65
TIER_PROMISING_THRESHOLD = 0.35

# 中立重み（cold start 時のデフォルト）
_NEUTRAL_WEIGHTS: dict[str, float] = {
    "price_focus": -0.3,
    "substance_talk": 0.4,
    "self_disclosure": 0.3,
    "early_purchase_signal": -0.1,
    "other": 0.0,
}


def _tier_from_score(score: float) -> ScoreTier:
    if score >= TIER_TOP_THRESHOLD:
        return ScoreTier.top
    if score >= TIER_PROMISING_THRESHOLD:
        return ScoreTier.promising
    return ScoreTier.watching


def compute_score(
    label_counts: dict[str, int],
    weights: dict[str, float],
    total_messages: int,
    is_cold_start: bool,
) -> tuple[float, float, ScoreTier]:
    """
    ラベル集計 + テナント重みからスコア・確信度・ティアを計算する純粋関数。

    ADR-107 §C: 裸の断定を返さない（スコア + 確信度 + ティアの3点セット）。
    thin-data（メッセージ0件）でも呼べる設計。
    """
    if total_messages == 0:
        return 0.5, 0.0, ScoreTier.watching

    raw = sum(
        (label_counts.get(label, 0) / total_messages) * weight
        for label, weight in weights.items()
    )
    # sigmoid-like: 常に [0, 1] に収める
    score = 0.5 + raw / (1.0 + abs(raw))
    score = max(0.0, min(1.0, score))

    # 確信度: メッセージ数 + cold start で段階的に低下
    conf = min(total_messages / MIN_MSG_CONFIDENCE, 1.0)
    if is_cold_start:
        conf *= 0.5

    return round(score, 3), round(conf, 3), _tier_from_score(score)


async def get_label_counts_for_lead(
    db: AsyncSession,
    lead_id: int,
) -> tuple[dict[str, int], int, int]:
    """
    meta_messages から lead_id のラベル分布を返す。
    (label_counts, total_messages, inbound_count) のタプル。

    注意: meta_messages.lead_id は NULL 許容のため IS NOT NULL を条件に含む。
    地域・国籍は使わない（行動のみ）。
    """
    result = await db.execute(
        text(
            """
            SELECT
                COUNT(*) FILTER (WHERE label = 'price_focus')            AS price_focus,
                COUNT(*) FILTER (WHERE label = 'substance_talk')         AS substance_talk,
                COUNT(*) FILTER (WHERE label = 'self_disclosure')        AS self_disclosure,
                COUNT(*) FILTER (WHERE label = 'early_purchase_signal')  AS early_purchase_signal,
                COUNT(*) FILTER (WHERE label = 'other')                  AS other_count,
                COUNT(*) FILTER (WHERE direction = 'inbound')            AS inbound_count,
                COUNT(*)                                                  AS total_count
            FROM message_labels
            WHERE lead_id = :lead_id
              AND source IN ('rule', 'llm', 'human')
            """
        ),
        {"lead_id": lead_id},
    )
    row = result.fetchone()
    if not row or row.total_count == 0:
        return {}, 0, 0

    counts = {
        "price_focus": int(row.price_focus),
        "substance_talk": int(row.substance_talk),
        "self_disclosure": int(row.self_disclosure),
        "early_purchase_signal": int(row.early_purchase_signal),
        "other": int(row.other_count),
    }
    return counts, int(row.total_count), int(row.inbound_count)


async def get_tenant_calibration(
    db: AsyncSession,
    tenant_id: int,
) -> tuple[dict[str, float], bool, int]:
    """
    tenant_calibrations の最新行からラベル重みを返す。
    未較正なら中立重みと is_cold_start=True を返す。
    Returns: (weights, is_cold_start, won_sample_size)
    """
    result = await db.execute(
        text(
            """
            SELECT label_weights, is_cold_start, win_sample_size
            FROM tenant_calibrations
            WHERE tenant_id = :tid
            ORDER BY calibrated_at DESC
            LIMIT 1
            """
        ),
        {"tid": tenant_id},
    )
    row = result.fetchone()
    if not row:
        return _NEUTRAL_WEIGHTS.copy(), True, 0

    weights = {**_NEUTRAL_WEIGHTS, **row.label_weights}
    return weights, bool(row.is_cold_start), int(row.win_sample_size)


async def calibrate_tenant_weights(
    db: AsyncSession,
    tenant_id: int,
) -> dict[str, float]:
    """
    成約/失注実績からラベル重みを較正して tenant_calibrations に保存する。

    ADR-107 §B②: 説明可能・thin-data で断定しない。
    アルゴリズム: ラベル出現率の差分（シンプルで説明可能、ロジスティック回帰不使用）。
    """
    won_result = await db.execute(
        text(
            """
            SELECT
                COUNT(*) FILTER (WHERE ml.label = 'price_focus')
                    * 1.0 / NULLIF(COUNT(*), 0)           AS price_focus_rate,
                COUNT(*) FILTER (WHERE ml.label = 'substance_talk')
                    * 1.0 / NULLIF(COUNT(*), 0)           AS substance_talk_rate,
                COUNT(*) FILTER (WHERE ml.label = 'self_disclosure')
                    * 1.0 / NULLIF(COUNT(*), 0)           AS self_disclosure_rate,
                COUNT(*) FILTER (WHERE ml.label = 'early_purchase_signal')
                    * 1.0 / NULLIF(COUNT(*), 0)           AS early_purchase_signal_rate,
                COUNT(DISTINCT ml.lead_id)                AS sample_leads
            FROM message_labels ml
            JOIN leads l ON l.id = ml.lead_id
            JOIN invoices i ON i.lead_id = l.id
            WHERE ml.direction = 'inbound'
              AND i.status != 'cancelled'
            """
        )
    )
    won_row = won_result.fetchone()

    lost_result = await db.execute(
        text(
            """
            SELECT
                COUNT(*) FILTER (WHERE ml.label = 'price_focus')
                    * 1.0 / NULLIF(COUNT(*), 0)           AS price_focus_rate,
                COUNT(*) FILTER (WHERE ml.label = 'substance_talk')
                    * 1.0 / NULLIF(COUNT(*), 0)           AS substance_talk_rate,
                COUNT(*) FILTER (WHERE ml.label = 'self_disclosure')
                    * 1.0 / NULLIF(COUNT(*), 0)           AS self_disclosure_rate,
                COUNT(*) FILTER (WHERE ml.label = 'early_purchase_signal')
                    * 1.0 / NULLIF(COUNT(*), 0)           AS early_purchase_signal_rate,
                COUNT(DISTINCT ml.lead_id)                AS sample_leads
            FROM message_labels ml
            JOIN leads l ON l.id = ml.lead_id
            JOIN deals d ON d.lead_id = l.id
            WHERE ml.direction = 'inbound'
              AND (d.status = 'lost' OR d.lost_reason IS NOT NULL)
            """
        )
    )
    lost_row = lost_result.fetchone()

    won_n = int(won_row.sample_leads or 0)
    lost_n = int(lost_row.sample_leads or 0)
    total_n = won_n + lost_n

    is_cold_start = total_n < MIN_CALIBRATION_SAMPLES

    label_keys = ["price_focus", "substance_talk", "self_disclosure", "early_purchase_signal"]
    weights: dict[str, float] = {}

    for key in label_keys:
        won_rate = float(getattr(won_row, f"{key}_rate") or 0)
        lost_rate = float(getattr(lost_row, f"{key}_rate") or 0)
        # 差分を重みに。thin-data（is_cold_start=True）では中立値でクリップ
        diff = won_rate - lost_rate
        if is_cold_start:
            weights[key] = _NEUTRAL_WEIGHTS[key]
        else:
            weights[key] = round(max(-1.0, min(1.0, diff)), 3)

    weights["other"] = 0.0

    await db.execute(
        text(
            """
            INSERT INTO tenant_calibrations
                (tenant_id, label_weights, win_sample_size, loss_sample_size, is_cold_start)
            VALUES (:tid, :weights::jsonb, :win_n, :loss_n, :cold)
            """
        ),
        {
            "tid": tenant_id,
            "weights": str(weights).replace("'", '"'),
            "win_n": won_n,
            "loss_n": lost_n,
            "cold": is_cold_start,
        },
    )
    await db.commit()
    return weights


async def label_lead_messages(
    db: AsyncSession,
    lead_id: int,
    tenant_id: int,
) -> int:
    """
    meta_messages からリードのメッセージを取得し、ルールベースでラベル付けして
    message_labels テーブルに保存する。既存ラベルはスキップ（冪等）。
    保存件数を返す。
    """
    rows_result = await db.execute(
        text(
            """
            SELECT id, message_text, direction
            FROM meta_messages
            WHERE lead_id = :lid
              AND lead_id IS NOT NULL
            ORDER BY created_at
            """
        ),
        {"lid": lead_id},
    )
    messages = rows_result.fetchall()
    if not messages:
        return 0

    existing_result = await db.execute(
        text("SELECT message_id FROM message_labels WHERE lead_id = :lid"),
        {"lid": lead_id},
    )
    existing_ids = {r[0] for r in existing_result.fetchall()}

    saved = 0
    for i, msg in enumerate(messages):
        if msg.id in existing_ids:
            continue

        label, confidence = _classify_message(msg.message_text or "", i == 0)

        await db.execute(
            text(
                """
                INSERT INTO message_labels
                    (tenant_id, message_id, lead_id, label, confidence, direction, source)
                VALUES (:tid, :mid, :lid, :label, :conf, :dir, 'rule')
                """
            ),
            {
                "tid": tenant_id,
                "mid": msg.id,
                "lid": lead_id,
                "label": label,
                "conf": confidence,
                "dir": msg.direction,
            },
        )
        saved += 1

    if saved > 0:
        await db.commit()
    return saved


def _classify_message(text_: str, is_first: bool) -> tuple[str, float]:
    """
    ルールベース分類。地域・国籍・言語パターンは使わない（行動のみ）。
    Returns: (label, confidence)
    """
    t = text_.lower()

    price_keywords = ["価格", "料金", "費用", "いくら", "安い", "高い", "コスト", "予算",
                      "price", "cost", "fee", "cheap", "expensive"]
    disclosure_keywords = ["うちの場合", "私が担当", "私たちは", "弊社では", "our company",
                           "we are", "i'm in charge"]
    substance_keywords = ["使い方", "機能", "仕組み", "どう使う", "試し", "導入",
                          "how to use", "functionality", "features", "implement"]
    early_buy_keywords = ["購入したい", "今すぐ", "即決", "今日中", "買いたい",
                          "want to buy", "purchase now", "order now"]

    if is_first and any(kw in t for kw in early_buy_keywords):
        return "early_purchase_signal", 0.7

    if any(kw in t for kw in price_keywords):
        return "price_focus", 0.8

    if any(kw in t for kw in disclosure_keywords):
        return "self_disclosure", 0.75

    if any(kw in t for kw in substance_keywords):
        return "substance_talk", 0.75

    return "other", 0.9


async def get_or_compute_score(
    db: AsyncSession,
    tenant_id: int,
    lead_id: int,
) -> CustomerScoreResponse:
    """
    customer_scores テーブルを参照し、最新スコアがあれば返す。
    なければラベル付け→重み取得→計算→UPSERT して返す。
    """
    existing = await db.execute(
        text(
            """
            SELECT score, confidence, tier, signal_summary, sample_size,
                   is_cold_start, override_score, override_note, scored_at
            FROM customer_scores
            WHERE lead_id = :lid
            """
        ),
        {"lid": lead_id},
    )
    row = existing.fetchone()
    if row:
        return _row_to_response(lead_id, row)

    return await _compute_and_persist(db, tenant_id, lead_id)


async def recompute_score(
    db: AsyncSession,
    tenant_id: int,
    lead_id: int,
) -> CustomerScoreResponse:
    """強制再計算（既存スコアを上書き）。"""
    return await _compute_and_persist(db, tenant_id, lead_id)


async def _compute_and_persist(
    db: AsyncSession,
    tenant_id: int,
    lead_id: int,
) -> CustomerScoreResponse:
    await label_lead_messages(db, lead_id, tenant_id)

    label_counts, total_msgs, inbound_count = await get_label_counts_for_lead(db, lead_id)
    weights, is_cold, won_n = await get_tenant_calibration(db, tenant_id)

    score, conf, tier = compute_score(label_counts, weights, total_msgs, is_cold)

    summary = SignalSummary(
        total_messages=total_msgs,
        inbound_count=inbound_count,
        price_focus_count=label_counts.get("price_focus", 0),
        substance_talk_count=label_counts.get("substance_talk", 0),
        self_disclosure_count=label_counts.get("self_disclosure", 0),
        early_purchase_signal_count=label_counts.get("early_purchase_signal", 0),
        other_count=label_counts.get("other", 0),
        won_deals_ref_count=won_n,
    )

    now = datetime.utcnow()
    await db.execute(
        text(
            """
            INSERT INTO customer_scores
                (tenant_id, lead_id, score, confidence, tier, signal_summary,
                 sample_size, is_cold_start, scored_at)
            VALUES
                (:tid, :lid, :score, :conf, :tier, :summary::jsonb,
                 :sample, :cold, :now)
            ON CONFLICT (lead_id) DO UPDATE SET
                score         = EXCLUDED.score,
                confidence    = EXCLUDED.confidence,
                tier          = EXCLUDED.tier,
                signal_summary = EXCLUDED.signal_summary,
                sample_size   = EXCLUDED.sample_size,
                is_cold_start = EXCLUDED.is_cold_start,
                scored_at     = EXCLUDED.scored_at
            """
        ),
        {
            "tid": tenant_id,
            "lid": lead_id,
            "score": score,
            "conf": conf,
            "tier": tier.value,
            "summary": summary.model_dump_json(),
            "sample": total_msgs,
            "cold": is_cold,
            "now": now,
        },
    )
    await db.commit()

    return CustomerScoreResponse(
        lead_id=lead_id,
        score=score,
        confidence=conf,
        tier=tier,
        signal_summary=summary,
        sample_size=total_msgs,
        is_cold_start=is_cold,
        override_score=None,
        override_note=None,
        scored_at=now,
    )


def _row_to_response(lead_id: int, row: object) -> CustomerScoreResponse:
    summary_data = row.signal_summary or {}
    if isinstance(summary_data, str):
        import json
        summary_data = json.loads(summary_data)
    summary = SignalSummary(**summary_data)

    return CustomerScoreResponse(
        lead_id=lead_id,
        score=float(row.score),
        confidence=float(row.confidence),
        tier=ScoreTier(row.tier),
        signal_summary=summary,
        sample_size=int(row.sample_size),
        is_cold_start=bool(row.is_cold_start),
        override_score=float(row.override_score) if row.override_score is not None else None,
        override_note=row.override_note,
        scored_at=row.scored_at,
    )
