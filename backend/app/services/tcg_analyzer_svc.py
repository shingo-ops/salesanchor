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

ENGINE_VERSION = "name-first-v2-cond-r4-e3b-e4"

# NOTE: apply_unit_unresolved_flag_for_job / apply_unit_from_condition_for_job は
# 循環インポート回避のため analyze_extraction_job 内で lazy import する
# (tcg_unit_recovery_svc → tcg_analyzer_svc の依存があるため)

# TCG解析システムは tenant_004 専用スキーマ
TCG_SCHEMA = "tenant_004"


# ---------------------------------------------------------------------------
# マスタロード
# ---------------------------------------------------------------------------


def load_lookup_maps(
    session: Session,
) -> tuple[dict, dict, dict, dict, dict, dict]:
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

    # --- 単位エイリアス → (canonical, kubun) --- ※ resolve_unit_v2 用
    rows = session.execute(
        text(
            f"""
            SELECT ua.alias_text, u.canonical, u.kubun, u.id
            FROM {TCG_SCHEMA}.unit_aliases ua
            JOIN {TCG_SCHEMA}.units u ON u.id = ua.unit_id
            WHERE u.is_active = TRUE
            """
        )
    ).fetchall()
    unit_alias_to_info: dict[str, tuple[str, str]] = {}
    for alias_text, canonical, kubun, uid in rows:
        unit_alias_to_info[alias_text] = (canonical, kubun or "")
    for canonical in list(unit_canonical_to_uuid.keys()):
        unit_alias_to_info.setdefault(canonical, (canonical, unit_alias_to_info.get(canonical, (canonical, ""))[1]))

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
        unit_alias_to_info,
    )


def load_product_kubun_type_map(session: Session) -> dict[str, str]:
    """
    商品コード → 商品区分 kubun_type マップをロードする。
    product_category_id が NULL の商品は含まない。

    GAS 対照: filterProductMasterByUnitCategoryV2_ 用の商品区分情報
    """
    rows = session.execute(
        text(
            f"""
            SELECT p.code, pc.kubun_type
            FROM {TCG_SCHEMA}.tcg_products p
            JOIN {TCG_SCHEMA}.tcg_product_categories pc ON pc.id = p.product_category_id
            WHERE p.is_active = TRUE
              AND p.product_category_id IS NOT NULL
            """
        )
    ).fetchall()
    return {r[0]: r[1] for r in rows}


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


def filter_product_codes_by_unit_kubun(
    product_codes: list[str],
    kubun: str,
    product_code_to_kubun_type: dict[str, str],
) -> list[str]:
    """
    unit kubun に基づいて商品コードリストを絞り込む。

    GAS 対照: filterProductMasterByUnitCategoryV2_ (SystemResolverV2.gs)
      '箱系' / '箱系大' (UC_BOX / UC_CARTON) → kubun_type='箱系' の商品に限定
      その他 → 絞り込みなし（全商品を返す）

    フィルタ後に候補がゼロになった場合はフォールバックとして全商品を返す。
    """
    if "箱系" not in kubun:
        return product_codes

    filtered = [
        c for c in product_codes
        if product_code_to_kubun_type.get(c) == "箱系"
    ]
    return filtered if filtered else product_codes


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
    旧実装（alias lookup のみ）。resolve_condition_v2 に置き換え済み。
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
# 状態解決 v2: GAS resolveCondition_ R1〜R4 ロジック移植
# ---------------------------------------------------------------------------


def load_condition_entries(session: Session) -> list[dict]:
    """
    priority > 0 の conditions 行を condEntries として返す。
    priority ASC → app_kubun 長 DESC → code ASC でソート済み（resolveCondition_ と同順）。

    GAS 対照: readConditionMaster() condEntries 構築 (investigate2.gs:8118-8125)
    code ASC タイブレーカーは GAS の R3 条件処理順（SHURI→PERI: CN0005→CN0006）を保証する。
    GAS 根拠: investigate2.gs:9705-9710 で No shrink box (CN0005) を Opened box (CN0006) より先に判定。
    """
    rows = session.execute(
        text(
            f"""
            SELECT c.id, c.code, c.canonical, c.priority,
                   c.app_kubun, c.search_kw, c.exclude_kw
            FROM {TCG_SCHEMA}.conditions c
            WHERE c.is_active = TRUE
              AND c.priority IS NOT NULL
              AND c.priority > 0
            ORDER BY c.priority ASC,
                     length(COALESCE(c.app_kubun, '')) DESC,
                     c.code ASC
            """
        )
    ).fetchall()
    return [
        {
            "cond_id": str(r[0]),
            "code": r[1],
            "canonical": r[2],
            "priority": r[3],
            "app_kubun": r[4] or "",
            "search_kw": r[5] or "",
            "exclude_kw": r[6] or "",
        }
        for r in rows
    ]


def app_kubun_matches(app_kubun_str: str, kubun: str) -> bool:
    """
    状態マスタの適用区分（カンマ区切り）と実際の kubun を照合する。

    GAS 対照: appKubunMatches_(appKubunStr, kubun) (investigate2.gs:9583-9596)
      空欄 = 全適用
      '箱系大': kubun に '箱系大' を含む
      '箱系'  : kubun に '箱系' を含み '箱系大' を含まない
      '単位不明': kubun === '不明' or ''
      その他   : kubun に kbn を含む（'パック系' 等）
    """
    if not app_kubun_str or not app_kubun_str.strip():
        return True  # 空 = 全適用
    for kbn in app_kubun_str.split(","):
        kbn = kbn.strip()
        if not kbn:
            continue
        if kbn == "箱系大":
            if "箱系大" in kubun:
                return True
        elif kbn == "箱系":
            if "箱系" in kubun and "箱系大" not in kubun:
                return True
        elif kbn == "単位不明":
            if kubun in ("不明", ""):
                return True
        else:
            if kbn in kubun:
                return True
    return False


def resolve_unit_v2(
    raw_unit: str,
    unit_alias_to_info: dict[str, tuple[str, str]],
) -> tuple[Optional[str], str, bool]:
    """
    raw_unit → (canonical, kubun, resolved)。
    未知語は (raw_unit, '不明', False)。空は (None, '', False)。

    GAS 対照: resolveUnit_() (investigate2.gs:9547-9561)
      完全一致 → aliasMap[w]
      小文字一致 → aliasMap[keys[i]]
      未知語 → {canonical: w, kubun: '不明', unitId: ''}
      null/'(なし)' → null
    """
    if not raw_unit or not raw_unit.strip():
        return (None, "", False)
    stripped = raw_unit.strip()
    if stripped in unit_alias_to_info:
        canonical, kubun = unit_alias_to_info[stripped]
        return (canonical, kubun, True)
    lower = stripped.lower()
    lower_map = {k.lower(): v for k, v in unit_alias_to_info.items()}
    if lower in lower_map:
        canonical, kubun = lower_map[lower]
        return (canonical, kubun, True)
    return (stripped, "不明", False)


def resolve_condition_v2(
    raw_state: str,
    raw_product_name: str,
    kubun: str,
    cond_entries: list[dict],
    cond_canonical_to_uuid: dict,
) -> tuple[Optional[str], Optional[str], str]:
    """
    (canonical, cond_id, basis) を返す。

    GAS 対照: resolveCondition_(stateWord, prodName, unitResult, cm)
              (investigate2.gs:9609-9661)

    R1 (priority=1): FLAG_SINGLE 語 — isBoxOrCase のとき flagNote を付ける
    R2 (priority=2): ダメージ/開封語 — appKubun で区分絞込
    R3 (priority=3): 特殊語（シュリなし / ペリなし / 未サーチ）
    R4a(priority=4): data-driven（通常品 / 未開封等）
    R4b(code):       単位既定フォールバック（kubun→Case/Sealed box/FLAG_SINGLE）
    """
    text_combined = (raw_state or "") + " " + (raw_product_name or "")
    is_box_or_case = "箱系" in kubun  # 箱系大 も '箱系' を含む

    # --- R1 pre-pass: isBoxOrCase のとき FLAG_SINGLE 語を検査 → flagNote ---
    flag_note = ""
    if is_box_or_case:
        for e in cond_entries:
            if e["priority"] != 1:
                continue
            s_kws = [k.strip() for k in e["search_kw"].split(",") if k.strip()]
            hit, matched_kw = match_keyword(text_combined, s_kws, [])
            if hit:
                flag_note = f"単品語あり・要確認({matched_kw})"
                break

    # --- Main loop (priority ASC, app_kubun 長 DESC — load_condition_entries でソート済み) ---
    for e in cond_entries:
        if not app_kubun_matches(e["app_kubun"], kubun):
            continue
        s_kws = [k.strip() for k in e["search_kw"].split(",") if k.strip()]
        x_kws = [k.strip() for k in e["exclude_kw"].split(",") if k.strip()]
        hit, matched_kw = match_keyword(text_combined, s_kws, x_kws)
        if not hit:
            continue
        prefix = f"{flag_note}," if flag_note else ""
        basis = f"{prefix}R{e['priority']}:{matched_kw}"
        return (e["canonical"], e["cond_id"], basis)

    # --- R4 code fallback: kubun のみで分岐 ---
    b4_prefix = f"{flag_note}," if flag_note else ""
    b4 = b4_prefix + "R4:単位既定"
    if "箱系大" in kubun:
        cid = _find_cond_id(cond_entries, "CN0001") or cond_canonical_to_uuid.get("Case")
        return ("Case", cid, b4)
    if "箱系" in kubun:
        cid = _find_cond_id(cond_entries, "CN0003") or cond_canonical_to_uuid.get("Sealed box")
        return ("Sealed box", cid, b4)

    # --- R5: パック既定 (GAS: applyPackConditionDefault, AnalysisV2PackCondition.gs:66-180) ---
    # unit=パック系(UN0003) かつ R4b で FLAG_SINGLE になった行を Searched pack に変換する。
    # GAS 実測: basisDist R5=60件、UN0003 の Searched pack=61件（残1件はキーワード直接マッチ）。
    if kubun == "パック系":
        cid = _find_cond_id(cond_entries, "CN0010") or cond_canonical_to_uuid.get("Searched pack")
        return ("Searched pack", cid, b4_prefix + "R5:パック既定")

    cid = _find_cond_id(cond_entries, "CN0008") or cond_canonical_to_uuid.get("FLAG_SINGLE")
    return ("FLAG_SINGLE", cid, b4 + ":単位不明")


def _find_cond_id(cond_entries: list[dict], code: str) -> Optional[str]:
    """condEntries から code で cond_id を引く。"""
    for e in cond_entries:
        if e["code"] == code:
            return e["cond_id"]
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
        unit_alias_to_info,
    ) = load_lookup_maps(session)

    cond_entries = load_condition_entries(session)
    search_kw, exclude_kw = load_product_keywords(session)
    product_codes = list(product_code_to_uuid.keys())
    product_code_to_kubun_type = load_product_kubun_type_map(session)

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

        # 単位解決 v2（商品フィルタより先に実行）
        unit_canonical, kubun, unit_resolved = resolve_unit_v2(raw_unit, unit_alias_to_info)
        unit_uuid = unit_canonical_to_uuid.get(unit_canonical) if unit_canonical else None

        if unit_resolved:
            stats["unit_resolved"] += 1

        # unit kubun で商品コードを絞り込み（GAS: filterProductMasterByUnitCategoryV2_）
        filtered_codes = filter_product_codes_by_unit_kubun(
            product_codes, kubun, product_code_to_kubun_type
        )

        # 商品照合
        matched_code, pid_basis, pid_resolved, candidates = match_pid_name_first(
            raw_product_name, filtered_codes, search_kw, exclude_kw
        )
        product_uuid = product_code_to_uuid.get(matched_code) if matched_code else None

        if pid_resolved:
            stats["pid_resolved"] += 1

        # 状態解決 v2
        condition_canonical, condition_uuid, condition_basis_str = resolve_condition_v2(
            raw_state, raw_product_name, kubun, cond_entries, cond_canonical_to_uuid
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
                "condition_basis": condition_basis_str,
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

    # --- E3b + E4 後処理（未解決フラグ・状態→単位逆引き）---
    # lazy import: tcg_unit_recovery_svc → tcg_analyzer_svc の循環インポートを回避
    from app.services.tcg_unit_recovery_svc import (  # noqa: PLC0415
        apply_unit_from_condition_for_job,
        apply_unit_unresolved_flag_for_job,
    )

    e3b = apply_unit_unresolved_flag_for_job(session, extraction_job_id, TCG_SCHEMA)
    e4 = apply_unit_from_condition_for_job(session, extraction_job_id, TCG_SCHEMA)
    if e3b["flagged"] or e4["resolved"]:
        session.commit()
    stats["e3b_flagged"] = e3b["flagged"]
    stats["e4_resolved"] = e4["resolved"]

    logger.info(
        "[tcg_analyzer] extraction_job=%s stats=%s", extraction_job_id, stats
    )
    return stats


__all__ = [
    "ENGINE_VERSION",
    "load_lookup_maps",
    "load_product_kubun_type_map",
    "load_product_keywords",
    "load_condition_entries",
    "normalize_en",
    "token_and_match",
    "match_one_kw",
    "match_keyword",
    "match_pid_name_first",
    "filter_product_codes_by_unit_kubun",
    "app_kubun_matches",
    "resolve_unit",
    "resolve_unit_v2",
    "resolve_condition",
    "resolve_condition_v2",
    "analyze_extraction_job",
]
