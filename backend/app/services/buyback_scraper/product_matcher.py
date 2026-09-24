"""
買取商品と自社マスタの自動紐付け。

ADR-157 Phase 3: 既存の LINE 解析キーワード辞書を横展開し、
buyback_shop_products.product_id を自動設定する。
"""
import json
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.tcg_analyzer_svc import match_keyword, normalize_en  # noqa: F401

logger = logging.getLogger(__name__)


async def load_product_keywords_async(db: AsyncSession):
    """検索ワード・除外ワードを非同期で全件ロード。

    Returns:
        search_kw: {(product_id, product_code): [keyword, ...]}
        exclude_kw: {(product_id, product_code): [keyword, ...]}
    """
    search_kw: dict[tuple[int, str], list[str]] = {}
    exclude_kw: dict[tuple[int, str], list[str]] = {}

    # 検索ワード
    result = await db.execute(text("""
        SELECT p.id, p.product_code, psk.keyword
        FROM public.product_search_keywords psk
        JOIN public.products p ON p.id = psk.product_id
        WHERE p.is_active = TRUE
        ORDER BY p.product_code, psk.position
    """))
    for row in result:
        pid = row[0]  # products.id (INTEGER)
        code = row[1]
        kw = row[2]
        key = (pid, code)
        search_kw.setdefault(key, []).append(kw)

    # 除外ワード
    result = await db.execute(text("""
        SELECT p.id, p.product_code, pek.keyword
        FROM public.product_exclude_keywords pek
        JOIN public.products p ON p.id = pek.product_id
        WHERE p.is_active = TRUE
        ORDER BY p.product_code, pek.position
    """))
    for row in result:
        pid = row[0]
        code = row[1]
        kw = row[2]
        key = (pid, code)
        exclude_kw.setdefault(key, []).append(kw)

    return search_kw, exclude_kw


async def match_buyback_products(db: AsyncSession) -> dict:
    """未紐付けの買取商品を自社マスタとマッチングする。

    マッチングロジック:
    - 候補0件 → match_status='unmatched', product_id=NULL
    - 候補1件 → match_status='auto', product_id=候補のID
    - 候補複数 → 最長キーワード優先でソートし、最長が一意なら 'auto'、同長が複数なら 'pending_review'

    Returns:
        {"auto": int, "pending_review": int, "unmatched": int, "skipped": int}
    """
    # public スキーマへの write には operator フラグが必要
    await db.execute(text("SET LOCAL app.is_operator = 'true'"))

    # 検索ワード・除外ワードをロード
    search_kw, exclude_kw = await load_product_keywords_async(db)

    if not search_kw:
        logger.warning("product_matcher: 検索ワードが0件。マッチング中止")
        return {"auto": 0, "pending_review": 0, "unmatched": 0, "skipped": 0}

    # 未紐付け商品を取得
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
        card_game = row[2]  # noqa: F841 (将来のゲーム別フィルタリング用)

        candidates = []

        for (pid, code), kws in search_kw.items():
            ex_kws = exclude_kw.get((pid, code), [])
            hit, matched_kw = match_keyword(product_name, kws, ex_kws)
            if hit and matched_kw:
                candidates.append({
                    "product_id": pid,
                    "product_code": code,
                    "keyword": matched_kw,
                    "kw_len": len(matched_kw),
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

        elif len(candidates) == 1:
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
            # 複数候補 → 最長キーワード優先でソート
            candidates.sort(key=lambda x: x["kw_len"], reverse=True)

            # 最長が一意なら auto、同長が複数なら pending_review
            top_len = candidates[0]["kw_len"]
            top_candidates = [c for c in candidates if c["kw_len"] == top_len]

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
        stats["auto"],
        stats["pending_review"],
        stats["unmatched"],
        stats["skipped"],
    )
    return stats
