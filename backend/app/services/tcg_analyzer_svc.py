"""
MIG-04 Phase 3: TCG 照合サービス。

feat/tcg-migration-phase2:backend/tcg_migration/analyzer.py のロジックを
backend/app/services 層に移植。

extraction_items → analysis_results へのキーワード照合・単位解決・状態解決を行う。
同期 SQLAlchemy Session を使用（Celery タスク / スクリプト実行から呼ぶため）。

エンジンバージョン: "name-first-v2"

キーワード照合エンジン (name-first-v2):
  GAS investigate2.gs の matchKeyword_ を正として移植。
  - normalizeEn_  : 全角英数記号(U+FF01-FF60) → 半角ASCII + 小文字化
  - matchOneKw_   : 純ASCII語は単語境界正規表現、日本語混じりは tokenAndMatch_
  - tokenAndMatch_: キーワードを空白トークン分割して全トークンAND照合
  - matchKeyword_ : normalizeEn_ → 除外KW → 検索KW（カンマ区切り各語を matchOneKw_）

TCG解析システムは tenant_004 専用スキーマ。全 SQL は tenant_004. で修飾する。
"""
from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

ENGINE_VERSION = "name-first-v2"

# TCG解析システムは tenant_004 専用スキーマ
TCG_SCHEMA = "tenant_004"


# ---------------------------------------------------------------------------
# マスタロード
# ---------------------------------------------------------------------------


def load_lookup_maps(
    session: Session,
) -> tuple[dict, dict, dict, dict, dict]:
    """
    照合に必要なルックアップマップを一括ロードする。

    Returns:
      product_code_to_uuid   : {code: uuid_str}
      unit_alias_to_canonical: {alias_text: canonical}
      unit_canonical_to_uuid : {canonical: uuid_str}
      cond_alias_to_canonical: {alias_text: canonical}
      cond_canonical_to_uuid : {canonical: uuid_str}
    """
    # --- 商品コード → UUID ---
    rows = session.execute(
        text(f"SELECT code, id FROM {TCG_SCHEMA}.tcg_products WHERE is_active = TRUE")
    ).fetchall()
    product_code_to_uuid: dict[str, str] = {r[0]: str(r[1]) for r in rows}

    # --- 単位エイリアス → canonical + UUID ---
    rows = session.execute(
        text(
            f"""
            SELECT ua.alias_text, u.canonical, u.id
            FROM {TCG_SCHEMA}.unit_aliases ua
            JOIN {TCG_SCHEMA}.units u ON u.id = ua.unit_id
            WHERE u.is_active = TRUE
            """
        )
    ).fetchall()
    unit_alias_to_canonical: dict[str, str] = {}
    unit_canonical_to_uuid: dict[str, str] = {}
    for alias_text, canonical, uid in rows:
        unit_alias_to_canonical[alias_text] = canonical
        unit_canonical_to_uuid[canonical] = str(uid)

    # canonical 自体もエイリアスとして登録（直接マッチ用）
    for canonical, uid in list(unit_canonical_to_uuid.items()):
        unit_alias_to_canonical.setdefault(canonical, canonical)

    # --- 状態エイリアス → canonical + UUID ---
    rows = session.execute(
        text(
            f"""
            SELECT ca.alias_text, c.canonical, c.id
            FROM {TCG_SCHEMA}.condition_aliases ca
            JOIN {TCG_SCHEMA}.conditions c ON c.id = ca.condition_id
            WHERE c.is_active = TRUE
            """
        )
    ).fetchall()
    cond_alias_to_canonical: dict[str, str] = {}
    cond_canonical_to_uuid: dict[str, str] = {}
    for alias_text, canonical, cid in rows:
        cond_alias_to_canonical[alias_text] = canonical
        cond_canonical_to_uuid[canonical] = str(cid)

    # canonical 自体もエイリアスとして登録
    for canonical, cid in list(cond_canonical_to_uuid.items()):
        cond_alias_to_canonical.setdefault(canonical, canonical)

    return (
        product_code_to_uuid,
        unit_alias_to_canonical,
        unit_canonical_to_uuid,
        cond_alias_to_canonical,
        cond_canonical_to_uuid,
    )


def load_product_keywords(
    session: Session,
) -> tuple[dict, dict]:
    """
    商品ごとの検索キーワード・除外キーワードをロードする。

    Returns:
      search_kw : {product_code: [kw1, kw2, ...]}
      exclude_kw: {product_code: [kw1, kw2, ...]}
    """
    # 検索キーワード
    rows = session.execute(
        text(
            f"""
            SELECT p.code, psk.keyword
            FROM {TCG_SCHEMA}.product_search_keywords psk
            JOIN {TCG_SCHEMA}.tcg_products p ON p.id = psk.product_id
            WHERE p.is_active = TRUE
            ORDER BY p.code, psk.position
            """
        )
    ).fetchall()
    search_kw: dict[str, list[str]] = {}
    for code, kw in rows:
        if code not in search_kw:
            search_kw[code] = []
        search_kw[code].append(kw)

    # 除外キーワード
    rows = session.execute(
        text(
            f"""
            SELECT p.code, pek.keyword
            FROM {TCG_SCHEMA}.product_exclude_keywords pek
            JOIN {TCG_SCHEMA}.tcg_products p ON p.id = pek.product_id
            WHERE p.is_active = TRUE
            ORDER BY p.code, pek.position
            """
        )
    ).fetchall()
    exclude_kw: dict[str, list[str]] = {}
    for code, kw in rows:
        if code not in exclude_kw:
            exclude_kw[code] = []
        exclude_kw[code].append(kw)

    return search_kw, exclude_kw


# ---------------------------------------------------------------------------
# キーワード照合エンジン (GAS investigate2.gs 移植)
# ---------------------------------------------------------------------------

# 全角英数記号 U+FF01-FF60 → 半角 ASCII U+0021-0060 への変換オフセット
_FULLWIDTH_OFFSET = 0xFEE0

# 純ASCII語判定: 0x20-0x7E のみで構成
_RE_PURE_ASCII = re.compile(r"^[\x20-\x7e]+$")

# 単語境界: 前後が [a-z] でない位置
# GAS: /(?<![a-z])word(?![a-z])/ — Python は (?<![a-z]) lookbehind OK
_RE_WORD_BOUNDARY_TEMPLATE = r"(?<![a-z]){word}(?![a-z])"


def normalize_en(s: str) -> str:
    """
    全角英数記号(U+FF01–FF60) → 半角ASCII(U+0021–0060) に変換し小文字化する。

    GAS 対照: investigate2.gs:9569 normalizeEn_
      return (s || '').replace(/[\\uFF01-\\uFF60]/g,
        c => String.fromCharCode(c.charCodeAt(0) - 0xFEE0)).toLowerCase();
    """
    result = []
    for ch in (s or ""):
        cp = ord(ch)
        if 0xFF01 <= cp <= 0xFF60:
            result.append(chr(cp - _FULLWIDTH_OFFSET))
        else:
            result.append(ch)
    return "".join(result).lower()


def token_and_match(kw: str, norm_text: str) -> bool:
    """
    日本語混じりキーワードの順不同トークンAND照合。

    GAS 対照: investigate2.gs:9730 tokenAndMatch_
      var kwNorm = normalizeEn_(kw);
      var tokens = kwNorm.split(/\\s+/).filter(t => t.length > 0);
      return tokens.every(t => normText.indexOf(t) >= 0);

    kw を normalize_en した上で空白分割し、全トークンが norm_text に含まれれば True。
    """
    kw_norm = normalize_en(kw)
    tokens = [t for t in re.split(r"\s+", kw_norm) if t]
    if not tokens:
        return False
    return all(t in norm_text for t in tokens)


def match_one_kw(kw: str, norm_text: str) -> bool:
    """
    1キーワードの照合。純ASCII語は単語境界、日本語混じりは token_and_match。

    GAS 対照: investigate2.gs:9977 matchOneKw_
      if (/^[\\x20-\\x7e]+$/.test(kw)) {
        var kwl = kw.toLowerCase().replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&');
        return /(?<![a-z])kwl(?![a-z])/.test(normText);
      }
      return tokenAndMatch_(kw, normText);
    """
    if not kw:
        return False
    if _RE_PURE_ASCII.match(kw):
        kwl = re.escape(kw.lower())
        pattern = _RE_WORD_BOUNDARY_TEMPLATE.format(word=kwl)
        return bool(re.search(pattern, norm_text))
    return token_and_match(kw, norm_text)


def match_keyword(
    text_raw: str,
    search_kw_str: list[str],
    exclude_kw_str: list[str],
) -> tuple[bool, Optional[str]]:
    """
    商品名に対して検索KW/除外KWを照合し (hit, matched_kw) を返す。

    GAS 対照: investigate2.gs:9995 matchKeyword_
      var normText = normalizeEn_(text);
      // 除外語チェック
      if (excludeKwStr) {
        var excl = String(excludeKwStr).split(',').some(kw => {
          kw = kw.trim(); return kw && matchOneKw_(kw, normText); });
        if (excl) return { hit: false, matchedKw: null };
      }
      // 検索語なし = 全マッチ
      if (!searchKwStr) return { hit: true, matchedKw: '(既定)' };
      // 検索語照合（カンマ区切り各語をmatchOneKw_）
      ...

    Args:
      text_raw      : 照合対象の生テキスト
      search_kw_str : 検索キーワードのリスト（DB から個別行で渡す）
      exclude_kw_str: 除外キーワードのリスト（同上）

    Returns:
      (hit, matched_kw_or_None)
    """
    norm_text = normalize_en(text_raw)

    # 除外語チェック（1語でも hit したら除外）
    for kw in exclude_kw_str:
        if kw and match_one_kw(kw, norm_text):
            return False, None

    # 検索語なし = 全マッチ（GAS と同様）
    if not search_kw_str:
        return True, "(既定)"

    for kw in search_kw_str:
        if kw and match_one_kw(kw, norm_text):
            return True, kw

    return False, None


# ---------------------------------------------------------------------------
# キーワード照合
# ---------------------------------------------------------------------------


def match_pid_name_first(
    raw_name: str,
    product_codes: list[str],
    search_kw: dict,
    exclude_kw: dict,
) -> tuple[Optional[str], str, bool, list[str]]:
    """
    raw_name に対してキーワード照合を行い product_code を解決する。

    最長マッチキーワードを持つ商品を優先する。
    除外キーワードにヒットした商品は候補から除外する。

    Returns:
      (matched_code, pid_basis, resolved, candidates)
      - 0 candidates → (None, "NONE", False, [])
      - 1 candidate  → (code, "SK:<kw>", True, [code])
      - 2+ candidates → (best_code, "MULTI(PM.../...):要確認", False, [codes])

    pid_basis は VARCHAR(100) に収まるよう截断する。
    """
    candidates: list[tuple[str, str, int]] = []  # (code, matched_kw, kw_len)

    for code in product_codes:
        kws = search_kw.get(code, [])
        ex_kws = exclude_kw.get(code, [])

        hit, matched_kw = match_keyword(raw_name, kws, ex_kws)
        if not hit or matched_kw is None:
            continue

        candidates.append((code, matched_kw, len(matched_kw)))

    if not candidates:
        return (None, "NONE", False, [])

    # 最長マッチ優先でソート
    candidates.sort(key=lambda x: x[2], reverse=True)

    if len(candidates) == 1:
        code, kw, _ = candidates[0]
        pid_basis = f"SK:{kw}"[:100]
        return (code, pid_basis, True, [code])

    # 複数候補: 最長マッチを返すが resolved=False
    codes = [c[0] for c in candidates]
    best_code, best_kw, _ = candidates[0]
    parts = "/".join(f"PM.{c}" for c in codes[:5])
    pid_basis = f"MULTI({parts}):要確認"[:100]
    return (best_code, pid_basis, False, codes)


# ---------------------------------------------------------------------------
# 単位・状態解決
# ---------------------------------------------------------------------------


def resolve_unit(
    raw_unit: str,
    unit_alias_to_canonical: dict,
) -> tuple[Optional[str], bool]:
    """
    raw_unit → (canonical, resolved_bool)。
    解決不能は (None, False)。
    """
    if not raw_unit or not raw_unit.strip():
        return (None, False)

    stripped = raw_unit.strip()

    # 完全一致
    if stripped in unit_alias_to_canonical:
        return (unit_alias_to_canonical[stripped], True)

    # 小文字一致
    lower = stripped.lower()
    lower_map = {k.lower(): v for k, v in unit_alias_to_canonical.items()}
    if lower in lower_map:
        return (lower_map[lower], True)

    return (None, False)


def resolve_condition(
    raw_state: str,
    cond_alias_to_canonical: dict,
) -> Optional[str]:
    """
    raw_state → canonical または None。
    """
    if not raw_state or not raw_state.strip():
        return None

    stripped = raw_state.strip()

    if stripped in cond_alias_to_canonical:
        return cond_alias_to_canonical[stripped]

    # 小文字一致
    lower = stripped.lower()
    lower_map = {k.lower(): v for k, v in cond_alias_to_canonical.items()}
    if lower in lower_map:
        return lower_map[lower]

    return None


# ---------------------------------------------------------------------------
# 数値正規化
# ---------------------------------------------------------------------------


def _parse_numeric(raw: str) -> Optional[float]:
    """
    カンマ・通貨記号・全角数字を除去して float に変換する。
    失敗したら None を返す。
    """
    if not raw or not raw.strip():
        return None

    # 全角数字 → 半角
    s = raw.strip()
    s = s.translate(str.maketrans("０１２３４５６７８９", "0123456789"))

    # 通貨記号・単位・スペースを除去
    import re
    s = re.sub(r"[^\d.,]", "", s)
    s = s.replace(",", "")

    try:
        return float(s) if s else None
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# 照合メイン
# ---------------------------------------------------------------------------


def analyze_extraction_job(session: Session, extraction_job_id: str) -> dict:
    """
    extraction_job の全 extraction_items に対して照合を実行し、
    analysis_results を INSERT/UPDATE (冪等) する。

    Args:
        session: 同期 SQLAlchemy Session
        extraction_job_id: UUID 文字列

    Returns:
        {total, pid_resolved, unit_resolved, needs_review}
    """
    # ルックアップマップをロード
    (
        product_code_to_uuid,
        unit_alias_to_canonical,
        unit_canonical_to_uuid,
        cond_alias_to_canonical,
        cond_canonical_to_uuid,
    ) = load_lookup_maps(session)

    search_kw, exclude_kw = load_product_keywords(session)
    product_codes = list(product_code_to_uuid.keys())

    # extraction_items を取得
    rows = session.execute(
        text(
            f"""
            SELECT id, raw_product_name, raw_quantity, raw_price, raw_unit, raw_state
            FROM {TCG_SCHEMA}.extraction_items
            WHERE extraction_job_id = :ej_id
            ORDER BY line_start, id
            """
        ),
        {"ej_id": extraction_job_id},
    ).fetchall()

    now = datetime.now(timezone.utc)
    stats = {"total": 0, "pid_resolved": 0, "unit_resolved": 0, "needs_review": 0}

    for row in rows:
        (
            item_id,
            raw_product_name,
            raw_quantity,
            raw_price,
            raw_unit,
            raw_state,
        ) = row

        stats["total"] += 1
        raw_product_name = raw_product_name or ""
        raw_unit = raw_unit or ""
        raw_state = raw_state or ""

        # 商品照合
        matched_code, pid_basis, pid_resolved, candidates = match_pid_name_first(
            raw_product_name, product_codes, search_kw, exclude_kw
        )
        product_uuid = product_code_to_uuid.get(matched_code) if matched_code else None

        if pid_resolved:
            stats["pid_resolved"] += 1

        # 単位解決
        unit_canonical, unit_resolved = resolve_unit(raw_unit, unit_alias_to_canonical)
        unit_uuid = unit_canonical_to_uuid.get(unit_canonical) if unit_canonical else None

        if unit_resolved:
            stats["unit_resolved"] += 1

        # 状態解決
        condition_canonical = resolve_condition(raw_state, cond_alias_to_canonical)
        condition_uuid = (
            cond_canonical_to_uuid.get(condition_canonical) if condition_canonical else None
        )

        # 数量・価格正規化
        quantity_normalized = _parse_numeric(raw_quantity or "")
        price_normalized = _parse_numeric(raw_price or "")

        # needs_review 判定
        review_reasons: list[str] = []
        if not pid_resolved:
            review_reasons.append("pid_unresolved")
        if len(candidates) > 1:
            review_reasons.append("multi_candidate")
        needs_review = len(review_reasons) > 0

        if needs_review:
            stats["needs_review"] += 1

        review_reasons_str = ",".join(review_reasons) if review_reasons else None

        # analysis_results を UPSERT (extraction_item_id に UNIQUE 制約あり)
        session.execute(
            text(
                f"""
                INSERT INTO {TCG_SCHEMA}.analysis_results (
                    id,
                    extraction_item_id,
                    product_id,
                    pid_resolved,
                    pid_basis,
                    unit_id,
                    unit_canonical,
                    unit_resolved,
                    condition_id,
                    condition_canonical,
                    condition_basis,
                    quantity_normalized,
                    price_normalized,
                    note_ja,
                    status,
                    exclusion,
                    needs_review,
                    review_reasons,
                    engine_version,
                    computed_at,
                    updated_at
                )
                VALUES (
                    :id,
                    :extraction_item_id,
                    :product_id,
                    :pid_resolved,
                    :pid_basis,
                    :unit_id,
                    :unit_canonical,
                    :unit_resolved,
                    :condition_id,
                    :condition_canonical,
                    :condition_basis,
                    :quantity_normalized,
                    :price_normalized,
                    NULL,
                    'active',
                    NULL,
                    :needs_review,
                    :review_reasons,
                    :engine_version,
                    :computed_at,
                    :updated_at
                )
                ON CONFLICT (extraction_item_id)
                DO UPDATE SET
                    product_id          = EXCLUDED.product_id,
                    pid_resolved        = EXCLUDED.pid_resolved,
                    pid_basis           = EXCLUDED.pid_basis,
                    unit_id             = EXCLUDED.unit_id,
                    unit_canonical      = EXCLUDED.unit_canonical,
                    unit_resolved       = EXCLUDED.unit_resolved,
                    condition_id        = EXCLUDED.condition_id,
                    condition_canonical = EXCLUDED.condition_canonical,
                    condition_basis     = EXCLUDED.condition_basis,
                    quantity_normalized = EXCLUDED.quantity_normalized,
                    price_normalized    = EXCLUDED.price_normalized,
                    needs_review        = EXCLUDED.needs_review,
                    review_reasons      = EXCLUDED.review_reasons,
                    engine_version      = EXCLUDED.engine_version,
                    computed_at         = EXCLUDED.computed_at,
                    updated_at          = EXCLUDED.updated_at
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "extraction_item_id": str(item_id),
                "product_id": product_uuid,
                "pid_resolved": pid_resolved,
                "pid_basis": pid_basis,
                "unit_id": unit_uuid,
                "unit_canonical": unit_canonical,
                "unit_resolved": unit_resolved,
                "condition_id": condition_uuid,
                "condition_canonical": condition_canonical,
                "condition_basis": condition_canonical,
                "quantity_normalized": quantity_normalized,
                "price_normalized": price_normalized,
                "needs_review": needs_review,
                "review_reasons": review_reasons_str,
                "engine_version": ENGINE_VERSION,
                "computed_at": now,
                "updated_at": now,
            },
        )

    session.commit()

    logger.info(
        "[tcg_analyzer] extraction_job=%s stats=%s", extraction_job_id, stats
    )
    return stats


__all__ = [
    "ENGINE_VERSION",
    "load_lookup_maps",
    "load_product_keywords",
    "normalize_en",
    "token_and_match",
    "match_one_kw",
    "match_keyword",
    "match_pid_name_first",
    "resolve_unit",
    "resolve_condition",
    "analyze_extraction_job",
]
