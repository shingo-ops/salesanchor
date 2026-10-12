"""型番（品番・マーク）が既存の有効商品と重なっていないかを判定する。

判定の唯一の場所。画面・CSV・登録スクリプトのどの入口もここを呼ぶ。
同じ判定を他の場所に書かない。DB は SELECT だけ。保存は止めない（警告を返すだけ）。

重なり: 渡された product_code・mark（空は除く）を normalize_for_match した値が、
有効な商品（public.products の is_active = TRUE、全作品）の product_code・mark の
正規化値と一致すること。

推奨する除外ワード（excl-official で使った規則と同じ）:
  - 相手の名前全体と、相手の検索ワードのうち相手の型番でない語を候補にする
  - 正規化後 3 文字未満の語は除く
  - 候補の正規化値が、受け手自身の名前・検索ワードの正規化値に含まれる語は除く
    （除外すると受け手自身が除外されるため）
  - 受け手が既に持つ除外ワードは除く
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.extraction_judgement_svc import normalize_for_match

MIN_SUGGEST_LEN = 3

_PRODUCTS_SQL = text(
    "SELECT p.id, p.name, p.product_code, p.mark, tm.name_ja "
    "FROM public.products p "
    "LEFT JOIN public.type_master tm ON tm.id = p.work_id "
    "WHERE p.is_active = TRUE "
    "AND ((p.product_code IS NOT NULL AND p.product_code <> '') "
    "OR (p.mark IS NOT NULL AND p.mark <> '')) "
    "ORDER BY p.id"
)
_SEARCH_WORDS_SQL = text(
    "SELECT product_id, keyword FROM public.product_search_keywords "
    "WHERE product_id = ANY(:ids) ORDER BY product_id, position"
)
_EXCLUDE_WORDS_SQL = text(
    "SELECT product_id, keyword FROM public.product_exclude_keywords "
    "WHERE product_id = ANY(:ids) ORDER BY product_id, position"
)


def _norm(value: str | None) -> str:
    return normalize_for_match(value or "")


def _clean(words: Sequence[str] | None) -> list[str]:
    return [w.strip() for w in (words or []) if w and w.strip()]


def _contains_any(norm_word: str, haystacks: Sequence[str]) -> bool:
    return any(norm_word in hay for hay in haystacks)


def _suggest(
    candidates: Sequence[str],
    receiver_texts: Sequence[str],
    receiver_excludes: Sequence[str],
) -> list[str]:
    """受け手に追加する除外ワードの候補。原文のまま、正規化値で重複を除いて返す。"""
    receiver_norm_texts = [_norm(t) for t in receiver_texts]
    already = {_norm(w) for w in receiver_excludes}
    seen: set[str] = set()
    result: list[str] = []
    for word in candidates:
        norm_word = _norm(word)
        if len(norm_word) < MIN_SUGGEST_LEN or norm_word in seen:
            continue
        if norm_word in already or _contains_any(norm_word, receiver_norm_texts):
            continue
        seen.add(norm_word)
        result.append(word)
    return result


def _effective_excludes(
    excludes: Sequence[str], opponent_texts: Sequence[str]
) -> list[str]:
    """除外ワードのうち、相手の名前・検索ワードに実際に当たるもの。"""
    opponent_norm = [_norm(t) for t in opponent_texts]
    return [
        w for w in excludes if _norm(w) and _contains_any(_norm(w), opponent_norm)
    ]


def _non_code_words(words: Sequence[str], code_norms: set[str]) -> list[str]:
    return [w for w in words if _norm(w) not in code_norms]


def _match(
    own_norms: set[str], product_code: str | None, mark: str | None
) -> tuple[str, str] | None:
    for field, value in (("product_code", product_code), ("mark", mark)):
        if _norm(value) and _norm(value) in own_norms:
            return field, str(value)
    return None


async def _load_words(
    db: AsyncSession, statement: Any, ids: list[int]
) -> dict[int, list[str]]:
    if not ids:
        return {}
    result = await db.execute(statement, {"ids": ids})
    words: dict[int, list[str]] = {}
    for product_id, keyword in result.fetchall():
        words.setdefault(int(product_id), []).append(str(keyword))
    return words


async def find_code_collisions(
    db: AsyncSession,
    *,
    product_code: str | None,
    mark: str | None,
    name: str,
    search_keywords: Sequence[str] | None,
    exclude_keywords: Sequence[str] | None,
    exclude_product_id: int | str | None = None,
) -> list[dict[str, Any]]:
    """型番が重なる有効商品を全部返す（件数の上限なし・1商品1件）。"""
    own_norms = {n for n in (_norm(product_code), _norm(mark)) if n}
    if not own_norms:
        return []

    own_search = _clean(search_keywords)
    own_exclude = _clean(exclude_keywords)
    own_code_norms = own_norms
    own_texts = [name, *own_search]
    skip_id = str(exclude_product_id) if exclude_product_id is not None else None

    rows = (await db.execute(_PRODUCTS_SQL)).fetchall()
    matched: list[tuple[Any, str, str]] = []
    for row in rows:
        if skip_id is not None and str(row[0]) == skip_id:
            continue
        hit = _match(own_norms, row[2], row[3])
        if hit is not None:
            matched.append((row, hit[0], hit[1]))
    if not matched:
        return []

    ids = [int(row[0]) for row, _, _ in matched]
    other_search = await _load_words(db, _SEARCH_WORDS_SQL, ids)
    other_exclude = await _load_words(db, _EXCLUDE_WORDS_SQL, ids)

    collisions: list[dict[str, Any]] = []
    for row, field, value in matched:
        pid = int(row[0])
        other_name = str(row[1] or "")
        other_words = other_search.get(pid, [])
        other_excl = other_exclude.get(pid, [])
        other_code_norms = {n for n in (_norm(row[2]), _norm(row[3])) if n}
        other_texts = [other_name, *other_words]
        collisions.append(
            {
                "product_id": str(pid),
                "name": other_name,
                "work_name": str(row[4] or ""),
                "matched_value": value,
                "matched_field": field,
                "suggest_add_to_this": _suggest(
                    [other_name, *_non_code_words(other_words, other_code_norms)],
                    own_texts,
                    own_exclude,
                ),
                "suggest_add_to_other": _suggest(
                    [name, *_non_code_words(own_search, own_code_norms)],
                    other_texts,
                    other_excl,
                ),
                "already_excluded_by_this": _effective_excludes(
                    own_exclude, other_texts
                ),
                "already_excluded_by_other": _effective_excludes(
                    other_excl, own_texts
                ),
            }
        )
    return collisions
