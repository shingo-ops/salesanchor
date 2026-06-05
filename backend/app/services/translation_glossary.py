from __future__ import annotations

"""
ADR-110: 翻訳グロッサリ管理サービス。

public.translation_glossary テーブルへの CRUD 操作と、
AI 翻訳プロンプトへのグロッサリ注入インターフェースを提供する。

商品マスタ（public.products）からの自動 seed も本モジュールが担う。
"""

import logging
from dataclasses import dataclass
from typing import Any, Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_TABLE = "public.translation_glossary"

# Sentinel: "パラメータ未指定" を None（= 訳さない）と区別するため
_UNSET: Any = object()

# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GlossaryEntry:
    id: int
    tenant_id: int | None
    source_term: str
    target_text: str | None       # None = 「訳さない」
    language_pair: str
    term_type: str
    is_active: bool
    source_ref: str | None
    notes: str | None
    # ADR-SA-17 昇格フロー（I-9）。既定 'none'。翻訳ロードでは未使用（既定のまま）。
    share_status: str = "none"


@dataclass(frozen=True)
class PromotionQueueItem:
    """昇格レビューキューの 1 件（ADR-SA-17 I-9）。

    匿名性のため提供テナント（tenant_id）は **意図的に含めない**。
    operator は語の内容のみをレビューする。
    """

    id: int
    source_term: str
    target_text: str | None
    language_pair: str
    term_type: str
    notes: str | None
    share_proposed_at: Any | None


@dataclass(frozen=True)
class GlossaryInstruction:
    """AI プロンプトに埋め込むグロッサリ指示の 1 エントリ。"""

    source_term: str
    instruction: str          # 例: "→ カービィ" or "→ そのまま保持（訳さない）"


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


async def load_glossary(
    db: AsyncSession,
    tenant_id: int,
    language_pair: str = "en->ja",
) -> list[GlossaryEntry]:
    """指定テナント + グローバル共有のグロッサリをロード。

    tenant_id のエントリが存在する場合はテナント側を優先（グローバルを上書き）。
    """
    result = await db.execute(
        text(
            f"SELECT id, tenant_id, source_term, target_text, language_pair, "
            f"term_type, is_active, source_ref, notes "
            f"FROM {_TABLE} "
            f"WHERE (tenant_id = :tenant_id OR tenant_id IS NULL) "
            f"  AND language_pair = :language_pair "
            f"  AND is_active = TRUE "
            f"ORDER BY tenant_id NULLS FIRST, lower(source_term)"
        ),
        {"tenant_id": tenant_id, "language_pair": language_pair},
    )
    rows = result.fetchall()

    # テナント側が同一 source_term で存在すればグローバルを上書き
    seen: dict[str, GlossaryEntry] = {}
    for row in rows:
        entry = GlossaryEntry(
            id=row[0],
            tenant_id=row[1],
            source_term=row[2],
            target_text=row[3],
            language_pair=row[4],
            term_type=row[5],
            is_active=row[6],
            source_ref=row[7],
            notes=row[8],
        )
        key = entry.source_term.lower()
        existing = seen.get(key)
        # テナント固有エントリは NULL（グローバル）より優先
        if existing is None or (existing.tenant_id is None and entry.tenant_id is not None):
            seen[key] = entry

    return list(seen.values())


def build_glossary_instructions(entries: Sequence[GlossaryEntry]) -> list[GlossaryInstruction]:
    """GlossaryEntry リストを AI プロンプト用指示リストに変換。"""
    instructions = []
    for entry in entries:
        if entry.target_text is None:
            inst = f"「{entry.source_term}」はそのまま原語を保持（訳さない）"
        else:
            inst = f"「{entry.source_term}」→「{entry.target_text}」と翻訳すること"
        instructions.append(GlossaryInstruction(
            source_term=entry.source_term,
            instruction=inst,
        ))
    return instructions


def format_glossary_for_prompt(entries: Sequence[GlossaryEntry]) -> str:
    """グロッサリ指示を AI プロンプト埋め込み用テキストに整形。

    エントリが空なら空文字列を返す。
    """
    if not entries:
        return ""
    instructions = build_glossary_instructions(entries)
    lines = [
        "## 必須用語対応表（これを厳守すること）",
        "以下の用語は指定通りに処理すること。自由に訳してはならない。",
        "",
    ]
    for inst in instructions:
        lines.append(f"- {inst.instruction}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


async def create_glossary_entry(
    db: AsyncSession,
    tenant_id: int | None,
    source_term: str,
    target_text: str | None,
    language_pair: str,
    term_type: str,
    notes: str | None = None,
    source_ref: str | None = None,
) -> GlossaryEntry:
    """グロッサリエントリを作成して返す。重複時は既存を上書き (upsert)。"""
    result = await db.execute(
        text(
            f"INSERT INTO {_TABLE} "
            "(tenant_id, source_term, target_text, language_pair, term_type, notes, source_ref, updated_at) "
            "VALUES (:tenant_id, :source_term, :target_text, :language_pair, :term_type, :notes, :source_ref, NOW()) "
            "ON CONFLICT (tenant_id, source_term, language_pair) DO UPDATE "
            "SET target_text = :target_text, term_type = :term_type, "
            "    notes = :notes, source_ref = :source_ref, "
            "    is_active = TRUE, updated_at = NOW() "
            "RETURNING id, tenant_id, source_term, target_text, language_pair, "
            "term_type, is_active, source_ref, notes, share_status"
        ),
        {
            "tenant_id": tenant_id,
            "source_term": source_term,
            "target_text": target_text,
            "language_pair": language_pair,
            "term_type": term_type,
            "notes": notes,
            "source_ref": source_ref,
        },
    )
    row = result.first()
    if row is None:
        raise RuntimeError("INSERT ... RETURNING が行を返しませんでした（DB 障害の可能性）")
    return GlossaryEntry(
        id=row[0], tenant_id=row[1], source_term=row[2], target_text=row[3],
        language_pair=row[4], term_type=row[5], is_active=row[6],
        source_ref=row[7], notes=row[8], share_status=row[9],
    )


async def update_glossary_entry(
    db: AsyncSession,
    entry_id: int,
    tenant_id: int,
    *,
    source_term: str | None = None,
    target_text: Any = _UNSET,  # _UNSET=未指定, None=「訳さない」, str=訳語
    term_type: str | None = None,
    notes: str | None = None,
    is_active: bool | None = None,
) -> GlossaryEntry | None:
    """グロッサリエントリを更新。tenant_id による所有権確認あり。

    target_text の扱い:
      - 省略（_UNSET）: 変更しない
      - None を明示: NULL に更新（「訳さない」= 原語保持）
      - str を渡す: その値に更新
    """
    updates: list[str] = ["updated_at = NOW()"]
    params: dict = {"entry_id": entry_id, "tenant_id": tenant_id}

    if source_term is not None:
        updates.append("source_term = :source_term")
        params["source_term"] = source_term
    if target_text is not _UNSET:
        updates.append("target_text = :target_text")
        params["target_text"] = target_text
    if term_type is not None:
        updates.append("term_type = :term_type")
        params["term_type"] = term_type
    if notes is not None:
        updates.append("notes = :notes")
        params["notes"] = notes
    if is_active is not None:
        updates.append("is_active = :is_active")
        params["is_active"] = is_active

    result = await db.execute(
        text(
            f"UPDATE {_TABLE} "
            f"SET {', '.join(updates)} "
            "WHERE id = :entry_id AND tenant_id = :tenant_id "
            "RETURNING id, tenant_id, source_term, target_text, language_pair, "
            "term_type, is_active, source_ref, notes, share_status"
        ),
        params,
    )
    row = result.first()
    if row is None:
        return None
    return GlossaryEntry(
        id=row[0], tenant_id=row[1], source_term=row[2], target_text=row[3],
        language_pair=row[4], term_type=row[5], is_active=row[6],
        source_ref=row[7], notes=row[8], share_status=row[9],
    )


async def delete_glossary_entry(
    db: AsyncSession,
    entry_id: int,
    tenant_id: int,
) -> bool:
    """テナント所有エントリを削除（グローバルエントリは削除不可）。"""
    result = await db.execute(
        text(
            f"DELETE FROM {_TABLE} "
            "WHERE id = :entry_id AND tenant_id = :tenant_id "
            "RETURNING id"
        ),
        {"entry_id": entry_id, "tenant_id": tenant_id},
    )
    return result.first() is not None


async def list_glossary(
    db: AsyncSession,
    tenant_id: int,
    language_pair: str | None = None,
    page: int = 1,
    per_page: int = 50,
) -> tuple[list[GlossaryEntry], int]:
    """グロッサリ一覧を返す。テナント固有 + グローバル共有の両方。"""
    lang_cond = "AND language_pair = :language_pair " if language_pair else ""
    lang_params: dict = {"tenant_id": tenant_id, "language_pair": language_pair or ""}
    offset = (page - 1) * per_page

    count_result = await db.execute(
        text(
            f"SELECT COUNT(*) FROM {_TABLE} "
            f"WHERE (tenant_id = :tenant_id OR tenant_id IS NULL) "
            f"{lang_cond}"
        ),
        lang_params,
    )
    total = count_result.scalar_one()

    result = await db.execute(
        text(
            f"SELECT id, tenant_id, source_term, target_text, language_pair, "
            f"term_type, is_active, source_ref, notes, share_status "
            f"FROM {_TABLE} "
            f"WHERE (tenant_id = :tenant_id OR tenant_id IS NULL) "
            f"{lang_cond}"
            f"ORDER BY tenant_id NULLS LAST, lower(source_term) "
            f"LIMIT :limit OFFSET :offset"
        ),
        {**lang_params, "limit": per_page, "offset": offset},
    )
    entries = [
        GlossaryEntry(
            id=row[0], tenant_id=row[1], source_term=row[2], target_text=row[3],
            language_pair=row[4], term_type=row[5], is_active=row[6],
            source_ref=row[7], notes=row[8], share_status=row[9],
        )
        for row in result.fetchall()
    ]
    return entries, total


# ---------------------------------------------------------------------------
# ADR-SA-17: 辞書2層化（Layer1 共有 / Layer2 私有）＋ 昇格フロー
# ---------------------------------------------------------------------------
#
# Layer1 共有ベース辞書 = tenant_id IS NULL（operator 管理・全テナント読み取り専用）
# Layer2 テナント私有辞書 = tenant_id = N（テナントが CRUD・RLS 分離）
#
# 昇格（I-9）: テナントが私有エントリに「共有提案」（share_status='proposed'）
#   → operator がレビュー → 承認で共有へ **匿名コピー**（提供テナント非開示）
#   → 私有エントリは残す（非破壊）。自動昇格はしない（operator 承認必須）。


async def propose_share(
    db: AsyncSession,
    entry_id: int,
    tenant_id: int,
) -> bool:
    """テナント私有エントリに「共有提案」フラグを立てる（I-9）。

    自テナント所有の私有エントリ（tenant_id 一致・共有エントリ不可）のみ対象。
    Returns True if updated, False if not found / not owned.
    """
    result = await db.execute(
        text(
            f"UPDATE {_TABLE} "
            "SET share_status = 'proposed', share_proposed_at = NOW(), updated_at = NOW() "
            "WHERE id = :entry_id AND tenant_id = :tenant_id "
            "  AND tenant_id IS NOT NULL "
            "RETURNING id"
        ),
        {"entry_id": entry_id, "tenant_id": tenant_id},
    )
    return result.first() is not None


async def list_promotion_queue(
    db: AsyncSession,
    page: int = 1,
    per_page: int = 50,
) -> tuple[list[PromotionQueueItem], int]:
    """昇格レビューキュー（share_status='proposed' の私有エントリ）を返す（operator 用）。

    匿名性のため tenant_id は返さない（PromotionQueueItem）。
    """
    offset = (page - 1) * per_page
    count_result = await db.execute(
        text(
            f"SELECT COUNT(*) FROM {_TABLE} "
            "WHERE tenant_id IS NOT NULL AND share_status = 'proposed'"
        )
    )
    total = count_result.scalar_one()

    result = await db.execute(
        text(
            f"SELECT id, source_term, target_text, language_pair, term_type, notes, "
            f"       share_proposed_at "
            f"FROM {_TABLE} "
            f"WHERE tenant_id IS NOT NULL AND share_status = 'proposed' "
            f"ORDER BY share_proposed_at ASC NULLS LAST, id ASC "
            f"LIMIT :limit OFFSET :offset"
        ),
        {"limit": per_page, "offset": offset},
    )
    items = [
        PromotionQueueItem(
            id=row[0],
            source_term=row[1],
            target_text=row[2],
            language_pair=row[3],
            term_type=row[4],
            notes=row[5],
            share_proposed_at=row[6],
        )
        for row in result.fetchall()
    ]
    return items, total


async def approve_promotion(
    db: AsyncSession,
    entry_id: int,
) -> bool:
    """提案中の私有エントリを共有ベースへ **匿名コピー** して承認する（I-9）。

    - 共有コピーは tenant_id NULL・提供テナント情報を一切持たない（匿名）。
    - 既に同一 (source_term, language_pair) の共有エントリがあれば更新（重複させない）。
    - 私有エントリは残し share_status='approved' にする（非破壊）。
    - 既に 'approved' / 'proposed' でない場合は no-op（冪等）。

    Returns True if approved, False if not found / already reviewed.
    """
    src = await db.execute(
        text(
            f"SELECT source_term, target_text, language_pair, term_type, notes "
            f"FROM {_TABLE} "
            "WHERE id = :entry_id AND tenant_id IS NOT NULL AND share_status = 'proposed'"
        ),
        {"entry_id": entry_id},
    )
    row = src.first()
    if row is None:
        return False
    source_term, target_text, language_pair, term_type, notes = row

    # 匿名共有コピー: 既存共有エントリがあれば更新、なければ挿入
    # （tenant_id NULL は UNIQUE 制約で衝突判定されないため手動 upsert）
    existing = await db.execute(
        text(
            f"SELECT id FROM {_TABLE} "
            "WHERE tenant_id IS NULL "
            "  AND lower(source_term) = lower(:source_term) "
            "  AND language_pair = :language_pair"
        ),
        {"source_term": source_term, "language_pair": language_pair},
    )
    existing_row = existing.first()
    if existing_row is not None:
        await db.execute(
            text(
                f"UPDATE {_TABLE} "
                "SET target_text = :target_text, term_type = :term_type, "
                "    notes = :notes, is_active = TRUE, source_ref = 'promoted', "
                "    updated_at = NOW() "
                "WHERE id = :id"
            ),
            {
                "id": existing_row[0],
                "target_text": target_text,
                "term_type": term_type,
                "notes": notes,
            },
        )
    else:
        await db.execute(
            text(
                f"INSERT INTO {_TABLE} "
                "(tenant_id, source_term, target_text, language_pair, term_type, "
                " source_ref, notes, share_status, updated_at) "
                "VALUES (NULL, :source_term, :target_text, :language_pair, :term_type, "
                "        'promoted', :notes, 'none', NOW())"
            ),
            {
                "source_term": source_term,
                "target_text": target_text,
                "language_pair": language_pair,
                "term_type": term_type,
                "notes": notes,
            },
        )

    # 私有エントリは残す（非破壊）。承認済みフラグのみ更新。
    await db.execute(
        text(
            f"UPDATE {_TABLE} "
            "SET share_status = 'approved', share_reviewed_at = NOW(), updated_at = NOW() "
            "WHERE id = :entry_id"
        ),
        {"entry_id": entry_id},
    )
    return True


async def reject_promotion(
    db: AsyncSession,
    entry_id: int,
) -> bool:
    """提案を却下する（私有エントリは残す・非破壊）。Returns True if rejected。"""
    result = await db.execute(
        text(
            f"UPDATE {_TABLE} "
            "SET share_status = 'rejected', share_reviewed_at = NOW(), updated_at = NOW() "
            "WHERE id = :entry_id AND tenant_id IS NOT NULL AND share_status = 'proposed' "
            "RETURNING id"
        ),
        {"entry_id": entry_id},
    )
    return result.first() is not None


# ---------------------------------------------------------------------------
# Layer1 共有辞書 CRUD（operator 専用・I-7）
# ---------------------------------------------------------------------------


async def list_shared_glossary(
    db: AsyncSession,
    language_pair: str | None = None,
    page: int = 1,
    per_page: int = 50,
) -> tuple[list[GlossaryEntry], int]:
    """共有ベース辞書（tenant_id IS NULL）の一覧を返す（operator 用）。"""
    lang_cond = "AND language_pair = :language_pair " if language_pair else ""
    params: dict = {"language_pair": language_pair or ""}
    offset = (page - 1) * per_page

    count_result = await db.execute(
        text(
            f"SELECT COUNT(*) FROM {_TABLE} "
            f"WHERE tenant_id IS NULL {lang_cond}"
        ),
        params,
    )
    total = count_result.scalar_one()

    result = await db.execute(
        text(
            f"SELECT id, tenant_id, source_term, target_text, language_pair, "
            f"term_type, is_active, source_ref, notes, share_status "
            f"FROM {_TABLE} "
            f"WHERE tenant_id IS NULL {lang_cond}"
            f"ORDER BY language_pair, lower(source_term) "
            f"LIMIT :limit OFFSET :offset"
        ),
        {**params, "limit": per_page, "offset": offset},
    )
    entries = [
        GlossaryEntry(
            id=row[0], tenant_id=row[1], source_term=row[2], target_text=row[3],
            language_pair=row[4], term_type=row[5], is_active=row[6],
            source_ref=row[7], notes=row[8], share_status=row[9],
        )
        for row in result.fetchall()
    ]
    return entries, total


async def update_shared_entry(
    db: AsyncSession,
    entry_id: int,
    *,
    source_term: str | None = None,
    target_text: Any = _UNSET,
    term_type: str | None = None,
    notes: str | None = None,
    is_active: bool | None = None,
) -> GlossaryEntry | None:
    """共有ベース辞書（tenant_id IS NULL）のエントリを更新（operator 専用）。"""
    updates: list[str] = ["updated_at = NOW()"]
    params: dict = {"entry_id": entry_id}

    if source_term is not None:
        updates.append("source_term = :source_term")
        params["source_term"] = source_term
    if target_text is not _UNSET:
        updates.append("target_text = :target_text")
        params["target_text"] = target_text
    if term_type is not None:
        updates.append("term_type = :term_type")
        params["term_type"] = term_type
    if notes is not None:
        updates.append("notes = :notes")
        params["notes"] = notes
    if is_active is not None:
        updates.append("is_active = :is_active")
        params["is_active"] = is_active

    result = await db.execute(
        text(
            f"UPDATE {_TABLE} "
            f"SET {', '.join(updates)} "
            "WHERE id = :entry_id AND tenant_id IS NULL "
            "RETURNING id, tenant_id, source_term, target_text, language_pair, "
            "term_type, is_active, source_ref, notes, share_status"
        ),
        params,
    )
    row = result.first()
    if row is None:
        return None
    return GlossaryEntry(
        id=row[0], tenant_id=row[1], source_term=row[2], target_text=row[3],
        language_pair=row[4], term_type=row[5], is_active=row[6],
        source_ref=row[7], notes=row[8], share_status=row[9],
    )


async def delete_shared_entry(
    db: AsyncSession,
    entry_id: int,
) -> bool:
    """共有ベース辞書（tenant_id IS NULL）のエントリを削除（operator 専用）。"""
    result = await db.execute(
        text(
            f"DELETE FROM {_TABLE} "
            "WHERE id = :entry_id AND tenant_id IS NULL "
            "RETURNING id"
        ),
        {"entry_id": entry_id},
    )
    return result.first() is not None


# ---------------------------------------------------------------------------
# 商品マスタ自動 seed（ADR-110 要件）
# ---------------------------------------------------------------------------


async def seed_glossary_from_products(
    db: AsyncSession,
    tenant_id: int,
    language_pair: str = "en->ja",
) -> int:
    """商品マスタ（public.products）の商品名を「訳さない」グロッサリとして seed する。

    既存エントリが同一 source_term で存在する場合はスキップ（上書きしない）。
    Returns: 追加したエントリ数
    """
    # public.products から英語名・日本語名を取得
    result = await db.execute(
        text(
            "SELECT DISTINCT name_en, name_ja "
            "FROM public.products "
            "WHERE (tenant_id = :tenant_id OR tenant_id IS NULL) "
            "  AND is_archived = FALSE "
            "  AND name_en IS NOT NULL AND name_en <> '' "
            "ORDER BY name_en"
        ),
        {"tenant_id": tenant_id},
    )
    rows = result.fetchall()
    if not rows:
        logger.info("[glossary_seed] products 0 件 (tenant_id=%s)", tenant_id)
        return 0

    count = 0
    for name_en, name_ja in rows:
        # すでに登録済みならスキップ
        exists_result = await db.execute(
            text(
                f"SELECT 1 FROM {_TABLE} "
                "WHERE (tenant_id = :tenant_id OR tenant_id IS NULL) "
                "  AND lower(source_term) = lower(:source_term) "
                "  AND language_pair = :language_pair"
            ),
            {
                "tenant_id": tenant_id,
                "source_term": name_en,
                "language_pair": language_pair,
            },
        )
        if exists_result.first() is not None:
            continue

        # target_text = NULL = 「訳さない」（英語商品名は注文・在庫の一意キーのため原語保持）
        # name_ja は notes に退避（参照用）
        await db.execute(
            text(
                f"INSERT INTO {_TABLE} "
                "(tenant_id, source_term, target_text, language_pair, term_type, source_ref, notes) "
                "VALUES (:tenant_id, :source_term, NULL, :language_pair, 'product_name', 'product_master', :notes) "
                "ON CONFLICT (tenant_id, source_term, language_pair) DO NOTHING"
            ),
            {
                "tenant_id": tenant_id,
                "source_term": name_en,
                "language_pair": language_pair,
                "notes": name_ja if name_ja else None,
            },
        )
        count += 1

    if count > 0:
        await db.commit()
        logger.info("[glossary_seed] %d 件 seed 完了 (tenant_id=%s)", count, tenant_id)

    return count


__all__ = [
    "GlossaryEntry",
    "GlossaryInstruction",
    "PromotionQueueItem",
    "approve_promotion",
    "build_glossary_instructions",
    "create_glossary_entry",
    "delete_glossary_entry",
    "delete_shared_entry",
    "format_glossary_for_prompt",
    "list_glossary",
    "list_promotion_queue",
    "list_shared_glossary",
    "load_glossary",
    "propose_share",
    "reject_promotion",
    "seed_glossary_from_products",
    "update_glossary_entry",
    "update_shared_entry",
]
