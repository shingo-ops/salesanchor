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
            "term_type, is_active, source_ref, notes"
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
    assert row is not None
    return GlossaryEntry(
        id=row[0], tenant_id=row[1], source_term=row[2], target_text=row[3],
        language_pair=row[4], term_type=row[5], is_active=row[6],
        source_ref=row[7], notes=row[8],
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
            "term_type, is_active, source_ref, notes"
        ),
        params,
    )
    row = result.first()
    if row is None:
        return None
    return GlossaryEntry(
        id=row[0], tenant_id=row[1], source_term=row[2], target_text=row[3],
        language_pair=row[4], term_type=row[5], is_active=row[6],
        source_ref=row[7], notes=row[8],
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
            f"term_type, is_active, source_ref, notes "
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
            source_ref=row[7], notes=row[8],
        )
        for row in result.fetchall()
    ]
    return entries, total


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
    "build_glossary_instructions",
    "create_glossary_entry",
    "delete_glossary_entry",
    "format_glossary_for_prompt",
    "list_glossary",
    "load_glossary",
    "seed_glossary_from_products",
    "update_glossary_entry",
]
