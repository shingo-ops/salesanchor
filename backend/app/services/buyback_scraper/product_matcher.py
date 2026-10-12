"""
買取商品と自社マスタの自動紐付け。

ADR-157 Phase 3: 既存の LINE 解析キーワード辞書を横展開し、
buyback_shop_products.product_id を自動設定する。

マッチングはスコア式:
- 各検索ワードのヒット文字数を加算（長いワード＝高得点）
- 除外ワードに1つでもヒット → その商品は即NG（候補から除外）
- 最高スコアの商品が1つだけ → 自動紐付け
- 同点が複数 → 人間確認（pending_review）
"""
import json
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.tcg_analyzer_svc import match_one_kw, match_product_search_keyword, normalize_en

logger = logging.getLogger(__name__)


def score_product(
    product_name_norm: str,
    search_kws: list[str],
    exclude_kws: list[str],
) -> tuple[int, list[str]]:
    """
    商品名に対するスコアを計算する。

    1. 除外ワードに1つでもヒット → 即NG（スコア-1、候補から除外）
    2. 検索ワード全件を評価し、ヒットしたキーワードの文字数を加算

    Returns:
        (score, matched_keywords)
        score = -1: 除外ワードヒット（NG）
        score = 0: ヒットなし
        score > 0: ヒットしたキーワード長の合計
    """
    for kw in exclude_kws:
        if kw and match_one_kw(kw, product_name_norm):
            return -1, []

    score = 0
    matched: list[str] = []
    for kw in search_kws:
        if kw and match_product_search_keyword(kw, product_name_norm):
            score += len(kw)
            matched.append(kw)

    return score, matched


async def load_product_keywords_async(db: AsyncSession):
    """検索ワード・除外ワードを非同期で全件ロード。

    Returns:
        search_kw: {(product_id, product_code): [keyword, ...]}
        exclude_kw: {(product_id, product_code): [keyword, ...]}
    """
    search_kw: dict[tuple[int, str], list[str]] = {}
    exclude_kw: dict[tuple[int, str], list[str]] = {}

    result = await db.execute(text("""
        SELECT p.id, p.product_code, psk.keyword
        FROM public.product_search_keywords psk
        JOIN public.products p ON p.id = psk.product_id
        WHERE p.is_active = TRUE
        ORDER BY p.product_code, psk.position
    """))
    for row in result:
        key = (row[0], row[1])
        search_kw.setdefault(key, []).append(row[2])

    result = await db.execute(text("""
        SELECT p.id, p.product_code, pek.keyword
        FROM public.product_exclude_keywords pek
        JOIN public.products p ON p.id = pek.product_id
        WHERE p.is_active = TRUE
        ORDER BY p.product_code, pek.position
    """))
    for row in result:
        key = (row[0], row[1])
        exclude_kw.setdefault(key, []).append(row[2])

    return search_kw, exclude_kw


async def match_buyback_products(db: AsyncSession) -> dict:
    """未紐付けの買取商品を自社マスタとスコア式マッチングする。

    Returns:
        {"auto": int, "pending_review": int, "unmatched": int, "skipped": int}
    """
    await db.execute(text("SET LOCAL app.is_operator = 'true'"))

    search_kw, exclude_kw = await load_product_keywords_async(db)

    if not search_kw:
        logger.warning("product_matcher: 検索ワードが0件。マッチング中止")
        return {"auto": 0, "pending_review": 0, "unmatched": 0, "skipped": 0}

    result = await db.execute(text("""
        SELECT id, product_name, card_game
        FROM public.buyback_shop_products
        WHERE match_status IN ('unmatched', 'pending_review')
          OR product_id IS NULL
        ORDER BY id
    """))
    unlinked = result.fetchall()

    stats = {"auto": 0, "pending_review": 0, "unmatched": 0, "skipped": 0}

    for row in unlinked:
        shop_product_id = row[0]
        product_name = row[1]

        norm_name = normalize_en(product_name)
        candidates = []

        for (pid, code), kws in search_kw.items():
            ex_kws = exclude_kw.get((pid, code), [])
            score, matched_kws = score_product(norm_name, kws, ex_kws)

            if score > 0:
                candidates.append({
                    "product_id": pid,
                    "product_code": code,
                    "score": score,
                    "keywords": matched_kws,
                })

        if not candidates:
            await db.execute(text("""
                UPDATE public.buyback_shop_products
                SET match_status = 'unmatched',
                    product_id = NULL,
                    match_candidates = NULL
                WHERE id = :id
            """), {"id": shop_product_id})
            stats["unmatched"] += 1
        else:
            candidates.sort(key=lambda x: x["score"], reverse=True)
            top_score = candidates[0]["score"]
            top_candidates = [c for c in candidates if c["score"] == top_score]

            if len(top_candidates) == 1:
                c = candidates[0]
                await db.execute(text("""
                    UPDATE public.buyback_shop_products
                    SET product_id = :pid,
                        match_status = 'auto',
                        match_candidates = :candidates
                    WHERE id = :id
                """), {
                    "id": shop_product_id,
                    "pid": c["product_id"],
                    "candidates": json.dumps(candidates),
                })
                stats["auto"] += 1
            else:
                await db.execute(text("""
                    UPDATE public.buyback_shop_products
                    SET product_id = NULL,
                        match_status = 'pending_review',
                        match_candidates = :candidates
                    WHERE id = :id
                """), {
                    "id": shop_product_id,
                    "candidates": json.dumps(candidates),
                })
                stats["pending_review"] += 1

    await db.commit()
    logger.info(
        "product_matcher: auto=%d, pending_review=%d, unmatched=%d, skipped=%d",
        stats["auto"], stats["pending_review"],
        stats["unmatched"], stats["skipped"],
    )
    return stats
