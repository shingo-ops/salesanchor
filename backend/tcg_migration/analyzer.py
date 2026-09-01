#!/usr/bin/env python3
"""
MIG-03 是正2: matching_name_first フラグ付きアナライザ

互換モード (flag=OFF): compat_engine.py と同じ compat-v1 値を UPDATE する
名前先行モード (flag=ON): 単位カテゴリ絞りをやめ商品名キーワードで直接解決する

主な変更点 (flag=ON 時):
  1. filterMasterByUnit_ による単位カテゴリ絞りを廃止
  2. 全商品に対してキーワード照合を行う
  3. 複数候補時: 最長一致を仮採用 + pid_basis="MULTI(...):要確認" + needs_review=True
  4. 単位不明時に 'Single' へ決めつける挙動を廃止（不明は unit_resolved=False のまま）
  5. 単位解決はキーワード照合とは独立に raw_unit → unit_aliases で行う

engine_version:
  flag=OFF → "compat-v1"
  flag=ON  → "name-first-v1"
"""

import json
import os
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

REPO_ROOT   = Path(__file__).resolve().parents[2]
GEMINI_FILE = Path.home() / "vs02_work" / "data" / "gemini_all.json"

sys.path.insert(0, str(REPO_ROOT))

DB_URL = os.environ.get("TCG_DB_URL",
         "postgresql+psycopg2://myapp_user:password@localhost:5432/myapp_db")
engine = create_engine(DB_URL, echo=False)

# ── 定数 ──────────────────────────────────────────────────────────────────────

ENGINE_VERSION_COMPAT    = "compat-v1"
ENGINE_VERSION_NAME_FIRST = "name-first-v1"


# ── ユーティリティ ─────────────────────────────────────────────────────────────

def parse_price(price_str) -> Decimal | None:
    if price_str is None:
        return None
    s = str(price_str).replace("円", "").replace(",", "").strip()
    if not s:
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def parse_qty(qty_val) -> Decimal | None:
    if qty_val is None or qty_val == "":
        return None
    try:
        return Decimal(str(qty_val))
    except InvalidOperation:
        return None


# ── マスタロード ──────────────────────────────────────────────────────────────

def load_lookup_maps(session: Session) -> tuple[dict, dict, dict, dict, dict]:
    """
    Returns:
      product_code_to_uuid  : {"PM0001": str_uuid, ...}
      unit_alias_to_canonical: {"BOX": "Box", "box": "Box", ...}
      unit_canonical_to_uuid : {"Box": str_uuid, ...}
      cond_alias_to_canonical: {"未開封": "Sealed box", ...}
      cond_canonical_to_uuid : {"Sealed box": str_uuid, ...}
    """
    prod_rows = session.execute(
        text("SELECT code, id FROM tcg_products")
    ).fetchall()
    product_code_to_uuid = {row[0]: str(row[1]) for row in prod_rows}

    # unit aliases: alias_text → canonical
    unit_rows = session.execute(
        text("SELECT ua.alias_text, u.canonical, u.id FROM unit_aliases ua JOIN units u ON u.id = ua.unit_id")
    ).fetchall()
    unit_alias_to_canonical = {row[0]: row[1] for row in unit_rows}
    unit_canonical_to_uuid  = {}
    for row in unit_rows:
        unit_canonical_to_uuid[row[1]] = str(row[2])

    # condition aliases: alias_text → canonical
    cond_rows = session.execute(
        text("SELECT ca.alias_text, c.canonical, c.id FROM condition_aliases ca JOIN conditions c ON c.id = ca.condition_id")
    ).fetchall()
    cond_alias_to_canonical = {row[0]: row[1] for row in cond_rows}
    cond_canonical_to_uuid  = {}
    for row in cond_rows:
        cond_canonical_to_uuid[row[1]] = str(row[2])

    return (
        product_code_to_uuid,
        unit_alias_to_canonical,
        unit_canonical_to_uuid,
        cond_alias_to_canonical,
        cond_canonical_to_uuid,
    )


def load_product_keywords(session: Session) -> tuple[dict, dict]:
    """
    Returns:
      search_kw : {product_code: [kw1, kw2, ...], ...}
      exclude_kw: {product_code: [kw1, kw2, ...], ...}
    """
    sk_rows = session.execute(
        text("SELECT p.code, psk.keyword FROM product_search_keywords psk JOIN tcg_products p ON p.id = psk.product_id")
    ).fetchall()
    search_kw: dict[str, list[str]] = {}
    for code, kw in sk_rows:
        search_kw.setdefault(code, []).append(kw)

    ek_rows = session.execute(
        text("SELECT p.code, pek.keyword FROM product_exclude_keywords pek JOIN tcg_products p ON p.id = pek.product_id")
    ).fetchall()
    exclude_kw: dict[str, list[str]] = {}
    for code, kw in ek_rows:
        exclude_kw.setdefault(code, []).append(kw)

    return search_kw, exclude_kw


# ── 名前先行マッチング ─────────────────────────────────────────────────────────

def match_pid_name_first(
    raw_name: str,
    product_codes: list[str],
    search_kw: dict[str, list[str]],
    exclude_kw: dict[str, list[str]],
) -> tuple[str | None, str | None, bool, list[str]]:
    """
    全商品に対してキーワード照合し、PID を解決する。

    Returns:
      (pid_code, pid_basis, pid_resolved, matched_codes_for_multi)

    0 candidates → (None, "NONE", False, [])
    1 candidate  → (code, "SK:<kw>", True, [code])
    2+ candidates → (longest_match_code, "MULTI(PM.../...):要確認", False, [codes...])
    """
    if not raw_name:
        return None, "NONE", False, []

    name_upper = raw_name  # 大文字小文字の正規化はしない（GAS に合わせる）

    # 各商品について (code, matched_kw) を収集
    candidates: list[tuple[str, str]] = []
    for code in product_codes:
        sks = search_kw.get(code, [])
        eks = exclude_kw.get(code, [])

        # 除外キーワード判定: いずれかが name に含まれたら候補外
        excluded = any(ek and ek in name_upper for ek in eks)
        if excluded:
            continue

        # 検索キーワード判定: いずれかが name に含まれたら候補に追加
        for kw in sks:
            if kw and kw in name_upper:
                candidates.append((code, kw))
                break  # 1 product につき 1 エントリ（先にマッチしたキーワードを使う）

    if not candidates:
        return None, "NONE", False, []

    if len(candidates) == 1:
        code, kw = candidates[0]
        return code, f"SK:{kw}", True, [code]

    # 複数候補: 最長マッチキーワードを持つ商品を仮採用
    candidates.sort(key=lambda x: len(x[1]), reverse=True)
    best_code, best_kw = candidates[0]
    all_codes_list = [c for c, _ in candidates]

    # pid_basis は VARCHAR(100) のため収まる範囲で切り詰める
    prefix = "MULTI("
    suffix = "):要確認"
    max_body = 100 - len(prefix) - len(suffix)
    body = "/".join(all_codes_list)
    if len(body) > max_body:
        body = body[:max_body]
        # 中途半端な PM コードを除去（最後の "/" 以降を削除）
        body = body.rsplit("/", 1)[0]
    pid_basis = f"{prefix}{body}{suffix}"

    return best_code, pid_basis, False, all_codes_list


# ── 単位解決 ─────────────────────────────────────────────────────────────────

def resolve_unit(raw_unit: str | None, unit_alias_to_canonical: dict[str, str]) -> tuple[str | None, bool]:
    """
    raw_unit → canonical 単位。解決不能は (None, False)。
    flag=ON では 'Single' へのフォールバックを行わない。
    """
    if not raw_unit:
        return None, False
    canonical = unit_alias_to_canonical.get(raw_unit)
    if canonical:
        return canonical, True
    return None, False


# ── 状態解決 ─────────────────────────────────────────────────────────────────

def resolve_condition(raw_state: str | None, cond_alias_to_canonical: dict[str, str]) -> str | None:
    if not raw_state:
        return None
    return cond_alias_to_canonical.get(raw_state)


# ── needs_review 判定 ──────────────────────────────────────────────────────────

def build_review(pid_resolved: bool, unit_resolved: bool, exclusion: str | None, extra_reasons: list[str] | None = None) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if not pid_resolved:
        reasons.append("PRODUCT_ID_UNRESOLVED")
    if not unit_resolved:
        reasons.append("UNIT_UNRESOLVED")
    if exclusion:
        reasons.append("EXCLUDED")
    if extra_reasons:
        reasons.extend(extra_reasons)
    return bool(reasons), reasons


# ── メインロジック ─────────────────────────────────────────────────────────────

def run_analyzer(session: Session, matching_name_first: bool) -> int:
    """
    全 extraction_items の analysis_results を UPDATE する。
    matching_name_first=True  → name-first-v1 ロジック
    matching_name_first=False → compat-v1 ロジック (gemini_all.json の system フィールドをそのままコピー)

    Returns: 更新行数
    """
    engine_version = ENGINE_VERSION_NAME_FIRST if matching_name_first else ENGINE_VERSION_COMPAT

    gemini = json.loads(GEMINI_FILE.read_text())

    (
        product_code_to_uuid,
        unit_alias_to_canonical,
        unit_canonical_to_uuid,
        cond_alias_to_canonical,
        cond_canonical_to_uuid,
    ) = load_lookup_maps(session)

    if matching_name_first:
        search_kw, exclude_kw = load_product_keywords(session)
        product_codes = sorted(product_code_to_uuid.keys())

        # extraction_items から raw_product_name / raw_unit / raw_state をロード
        ei_rows = session.execute(
            text("SELECT id, raw_product_name, raw_unit, raw_state FROM extraction_items")
        ).fetchall()
        ei_info: dict[str, dict] = {
            str(row[0]): {"raw_name": row[1], "raw_unit": row[2], "raw_state": row[3]}
            for row in ei_rows
        }

    updated = 0
    for item in gemini:
        ei_raw = item["extraction_item_id"].replace("EIV2-", "")
        sys_v  = item.get("system", {})
        gem_v  = item.get("gemini", {})

        qty   = parse_qty(gem_v.get("quantity"))
        price = parse_price(gem_v.get("price"))
        note  = sys_v.get("note") or None

        if not matching_name_first:
            # ── compat モード: system フィールドをそのままコピー ──────────────
            ri  = item.get("review_issues", [])

            pid_code       = sys_v.get("product_id", "") or ""
            product_uuid   = product_code_to_uuid.get(pid_code) if pid_code else None
            pid_resolved   = sys_v.get("pid_resolved", "NO") == "YES"
            pid_basis      = sys_v.get("pid_basis") or None

            unit_canonical = sys_v.get("unit") or None
            unit_uuid      = unit_canonical_to_uuid.get(unit_canonical) if unit_canonical else None
            unit_resolved  = sys_v.get("unit_resolved", "NO") == "YES"

            cond_canonical = sys_v.get("condition") or None
            cond_uuid      = cond_canonical_to_uuid.get(cond_canonical) if cond_canonical else None

            needs  = bool(ri)
            review = json.dumps(ri, ensure_ascii=False) if ri else None
            status = sys_v.get("status") or None
            excl   = sys_v.get("exclusion") or None

        else:
            # ── name-first モード ─────────────────────────────────────────────
            ei_data  = ei_info.get(ei_raw, {})
            raw_name  = ei_data.get("raw_name") or ""
            raw_unit  = ei_data.get("raw_unit") or ""
            raw_state = ei_data.get("raw_state") or ""

            # PID 解決
            pid_code, pid_basis, pid_resolved, _ = match_pid_name_first(
                raw_name, product_codes, search_kw, exclude_kw
            )
            product_uuid = product_code_to_uuid.get(pid_code) if pid_code else None

            # 単位解決 (カテゴリ絞りなし、Single フォールバックなし)
            unit_canonical, unit_resolved = resolve_unit(raw_unit, unit_alias_to_canonical)
            unit_uuid = unit_canonical_to_uuid.get(unit_canonical) if unit_canonical else None

            # 状態解決
            cond_canonical = resolve_condition(raw_state, cond_alias_to_canonical)
            cond_uuid = cond_canonical_to_uuid.get(cond_canonical) if cond_canonical else None

            # exclusion: マスタ未登録かつ pid_resolved=False
            if not pid_resolved and pid_basis == "NONE":
                excl = f"マスタ未登録: {raw_name}" if raw_name else "マスタ未登録"
            else:
                excl = None

            status = None  # name-first では status を再計算しない

            needs, reasons = build_review(pid_resolved, unit_resolved, excl)
            review = json.dumps(reasons, ensure_ascii=False) if reasons else None

        session.execute(text("""
            UPDATE analysis_results SET
                product_id          = :product_id,
                pid_resolved        = :pid_resolved,
                pid_basis           = :pid_basis,
                unit_id             = :unit_id,
                unit_canonical      = :unit_canonical,
                unit_resolved       = :unit_resolved,
                condition_id        = :condition_id,
                condition_canonical = :condition_canonical,
                quantity_normalized = :qty,
                price_normalized    = :price,
                note_ja             = :note,
                status              = :status,
                exclusion           = :exclusion,
                needs_review        = :needs_review,
                review_reasons      = :review_reasons,
                engine_version      = :engine_version,
                updated_at          = now()
            WHERE extraction_item_id = CAST(:ei_id AS uuid)
        """), {
            "product_id":           product_uuid,
            "pid_resolved":         pid_resolved,
            "pid_basis":            pid_basis,
            "unit_id":              unit_uuid,
            "unit_canonical":       unit_canonical,
            "unit_resolved":        unit_resolved,
            "condition_id":         cond_uuid,
            "condition_canonical":  cond_canonical,
            "qty":                  qty,
            "price":                price,
            "note":                 note,
            "status":               status,
            "exclusion":            excl,
            "needs_review":         needs,
            "review_reasons":       review,
            "engine_version":       engine_version,
            "ei_id":                ei_raw,
        })
        updated += 1

    return updated


# ── before/after 計測 ─────────────────────────────────────────────────────────

def measure(session: Session) -> dict:
    total     = session.execute(text("SELECT COUNT(*) FROM analysis_results")).scalar()
    needs_rev = session.execute(text("SELECT COUNT(*) FROM analysis_results WHERE needs_review")).scalar()
    pid_unres = session.execute(text("SELECT COUNT(*) FROM analysis_results WHERE NOT pid_resolved")).scalar()
    unit_unres= session.execute(text("SELECT COUNT(*) FROM analysis_results WHERE NOT unit_resolved")).scalar()
    return {
        "total": total,
        "needs_review": needs_rev,
        "pid_unresolved": pid_unres,
        "unit_unresolved": unit_unres,
    }


# ── main ───────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="MIG-03 是正2 アナライザ")
    parser.add_argument(
        "--flag", choices=["on", "off"], default="off",
        help="matching_name_first フラグ (on=名前先行モード / off=互換モード)"
    )
    args = parser.parse_args()
    matching_name_first = (args.flag == "on")

    mode = "name-first-v1" if matching_name_first else "compat-v1 (互換モード)"
    print(f"MIG-03 是正2 analyzer — モード: {mode}")

    with Session(engine) as s:
        before = measure(s)

    print(f"\n[BEFORE]")
    for k, v in before.items():
        print(f"  {k}: {v}")

    with Session(engine) as session:
        with session.begin():
            updated = run_analyzer(session, matching_name_first)

    print(f"\n  → {updated} 行を UPDATE")

    with Session(engine) as s:
        after = measure(s)

    print(f"\n[AFTER]")
    for k, v in after.items():
        print(f"  {k}: {v}")

    print("\n" + "=" * 60)
    print("差分レポート")
    print("=" * 60)

    compat_expected = {
        "total": 1626,
        "needs_review": 1394,
        "pid_unresolved": 344,
        "unit_unresolved": 528,
    }

    if not matching_name_first:
        # 互換モード: compat-v1 と完全一致を期待
        all_ok = True
        for k, exp in compat_expected.items():
            act = after[k]
            ok = (act == exp)
            mark = "OK" if ok else "MISMATCH"
            if not ok:
                all_ok = False
            print(f"  {k:<25} after={act:>6}  expected={exp:>6}  {mark}")
        print("=" * 60)
        if all_ok:
            print("  → compat-v1 ロールバック PASS")
        else:
            print("  → compat-v1 ロールバック FAIL")
            sys.exit(1)
    else:
        # 名前先行モード: before との差分を表示 (degradation チェック)
        for k, bv in before.items():
            av = after[k]
            delta = av - bv
            sign = "+" if delta >= 0 else ""
            print(f"  {k:<25} before={bv:>6}  after={av:>6}  delta={sign}{delta}")
        print("=" * 60)
        print("  → 悪化行の詳細確認が必要な場合は別途クエリで確認してください")


if __name__ == "__main__":
    main()
