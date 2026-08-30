#!/usr/bin/env python3
"""
MIG-03 是正1: 全 analysis_results の再解析（UPDATE ベース）。

compat_engine の論理と同じ値を使って全行を UPDATE する。
item_notes は extraction_items に紐付いているため、
analysis_results の UPDATE では一切影響を受けない。
これを verification として確認する。
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

ENGINE_VERSION = "compat-v1"


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


def load_lookup_maps(session: Session):
    prod_rows = session.execute(text("SELECT code, id FROM tcg_products")).fetchall()
    product_code_to_uuid = {row[0]: str(row[1]) for row in prod_rows}
    unit_rows = session.execute(text("SELECT canonical, id FROM units")).fetchall()
    unit_canonical_to_uuid = {row[0]: str(row[1]) for row in unit_rows}
    cond_rows = session.execute(text("SELECT canonical, id FROM conditions")).fetchall()
    cond_canonical_to_uuid = {row[0]: str(row[1]) for row in cond_rows}
    return product_code_to_uuid, unit_canonical_to_uuid, cond_canonical_to_uuid


def main():
    print("MIG-03 是正1: 全件再解析（UPDATE ベース）")

    # ── before ──────────────────────────────────────────────────────
    with Session(engine) as s:
        notes_before = s.execute(text("SELECT COUNT(*) FROM item_notes")).scalar()
        ar_before    = s.execute(text("SELECT COUNT(*) FROM analysis_results")).scalar()
        nr_before    = s.execute(text("SELECT COUNT(*) FROM analysis_results WHERE needs_review")).scalar()
        pid_before   = s.execute(text("SELECT COUNT(*) FROM analysis_results WHERE NOT pid_resolved")).scalar()
        unit_before  = s.execute(text("SELECT COUNT(*) FROM analysis_results WHERE NOT unit_resolved")).scalar()

    print(f"\n[BEFORE] item_notes={notes_before}  analysis_results={ar_before}")
    print(f"         needs_review={nr_before}  pid_unresolved={pid_before}  unit_unresolved={unit_before}")

    if notes_before == 0:
        print("  ⚠️  item_notes が 0 件です。先に item_notes を作成してください。")
        sys.exit(1)

    gemini = json.loads(GEMINI_FILE.read_text())

    with Session(engine) as session:
        with session.begin():
            product_code_to_uuid, unit_canonical_to_uuid, cond_canonical_to_uuid = \
                load_lookup_maps(session)

            updated = 0
            for item in gemini:
                ei_raw   = item["extraction_item_id"].replace("EIV2-", "")
                sys_v    = item.get("system", {})
                gem_v    = item.get("gemini", {})
                ri       = item.get("review_issues", [])

                pid_code       = sys_v.get("product_id", "") or ""
                product_uuid   = product_code_to_uuid.get(pid_code) if pid_code else None
                pid_resolved   = sys_v.get("pid_resolved", "NO") == "YES"
                pid_basis      = sys_v.get("pid_basis") or None

                unit_canonical = sys_v.get("unit") or None
                unit_uuid      = unit_canonical_to_uuid.get(unit_canonical) if unit_canonical else None
                unit_resolved  = sys_v.get("unit_resolved", "NO") == "YES"

                cond_canonical = sys_v.get("condition") or None
                cond_uuid      = cond_canonical_to_uuid.get(cond_canonical) if cond_canonical else None

                qty    = parse_qty(gem_v.get("quantity"))
                price  = parse_price(gem_v.get("price"))
                needs  = bool(ri)
                review = json.dumps(ri, ensure_ascii=False) if ri else None
                note   = sys_v.get("note") or None
                status = sys_v.get("status") or None
                excl   = sys_v.get("exclusion") or None

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
                    "product_id":      product_uuid,
                    "pid_resolved":    pid_resolved,
                    "pid_basis":       pid_basis,
                    "unit_id":         unit_uuid,
                    "unit_canonical":  unit_canonical,
                    "unit_resolved":   unit_resolved,
                    "condition_id":    cond_uuid,
                    "condition_canonical": cond_canonical,
                    "qty":             qty,
                    "price":           price,
                    "note":            note,
                    "status":          status,
                    "exclusion":       excl,
                    "needs_review":    needs,
                    "review_reasons":  review,
                    "engine_version":  ENGINE_VERSION,
                    "ei_id":           ei_raw,
                })
                updated += 1

    print(f"\n  → {updated} 行を UPDATE")

    # ── after ───────────────────────────────────────────────────────
    with Session(engine) as s:
        notes_after  = s.execute(text("SELECT COUNT(*) FROM item_notes")).scalar()
        ar_after     = s.execute(text("SELECT COUNT(*) FROM analysis_results")).scalar()
        nr_after     = s.execute(text("SELECT COUNT(*) FROM analysis_results WHERE needs_review")).scalar()
        pid_after    = s.execute(text("SELECT COUNT(*) FROM analysis_results WHERE NOT pid_resolved")).scalar()
        unit_after   = s.execute(text("SELECT COUNT(*) FROM analysis_results WHERE NOT unit_resolved")).scalar()

    print(f"\n[AFTER]  item_notes={notes_after}  analysis_results={ar_after}")
    print(f"         needs_review={nr_after}  pid_unresolved={pid_after}  unit_unresolved={unit_after}")

    print("\n" + "=" * 60)
    print("是正1 検証結果")
    print("=" * 60)
    checks = [
        ("item_notes 残存",     notes_before, notes_after,  True),
        ("analysis_results 総数", ar_before, ar_after,      True),
        ("needs_review",        nr_before,   nr_after,       True),
        ("pid_unresolved",      pid_before,  pid_after,      True),
        ("unit_unresolved",     unit_before, unit_after,     True),
    ]
    all_ok = True
    for label, before, after, expect_same in checks:
        if expect_same:
            ok = (before == after)
            mark = "✅ OK" if ok else "❌ MISMATCH"
            if not ok:
                all_ok = False
            print(f"  {label:<30} before={before}  after={after}  {mark}")

    print("=" * 60)
    if all_ok:
        print("  → 是正1 PASS: メモ孤立なし / 検収数字変化なし")
    else:
        print("  → 是正1 FAIL: STOP — 構造に問題あり")
        sys.exit(1)


if __name__ == "__main__":
    main()
