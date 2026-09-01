#!/usr/bin/env python3
"""
MIG-02 Phase 3: Compat Engine (互換モード)
gemini_all.json の `system` フィールドに格納された ProviderScoringV2 の
事前計算済みスコアリング結果を analysis_results テーブルに書き込む。

設計方針:
  - Gemini API 呼び出しなし
  - ProviderScoringV2 再実行なし
  - gemini_all.json の system フィールドをそのままコピーする「互換モード」
  - engine_version = "compat-v1"

ProviderScoringV2 スコアリングアルゴリズム概要 (GAS実装から逆引き):
  1. filterMasterByUnit_(productRows, unitId, categoryJaIndex)
     - 単位に対応するカテゴリ分類 (Box / Single) でマスタ行を絞り込む
  2. matchPid_(name, candidates, searchIdx, excludeIdx, pidIdx, rules)
     - Search Keywords に name が部分一致 && Exclude Keywords に不一致 → PID 解決
     - pid_basis: マッチしたキーワード "SK:<keyword>" または "NONE"
  3. resolveUnit_(rawUnit, unitAliases)
     - 単位エイリアステーブルで canonical を解決; 解決不能は unit_resolved=NO
  4. resolveCondition_(rawState, conditionAliases)
     - 状態エイリアステーブルで canonical を解決
  5. note, status, exclusion を付与
     - exclusion 条件: pid_resolved=NO かつマスタ未登録 → "マスタ未登録: ..."
  6. needs_review = pid_resolved=NO OR unit_resolved=NO OR exclusion!=''
     - review_reasons: ["PRODUCT_ID_UNRESOLVED", "UNIT_UNRESOLVED",
                        "EXCLUDED", "PRODUCT_MASTER_UNREGISTERED"]
"""

import json
import os
import sys
import uuid
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# ── パス設定 ──────────────────────────────────────────────────────────────────
REPO_ROOT   = Path(__file__).resolve().parents[2]
GEMINI_FILE = Path.home() / "vs02_work" / "data" / "gemini_all.json"

sys.path.insert(0, str(REPO_ROOT))
from tcg_migration.models import AnalysisResult

# ── DB接続 ─────────────────────────────────────────────────────────────────────
DB_URL = os.environ.get("TCG_DB_URL",
         "postgresql+psycopg2://myapp_user:password@localhost:5432/myapp_db")
engine = create_engine(DB_URL, echo=False)

ENGINE_VERSION = "compat-v1"

# ── ユーティリティ ─────────────────────────────────────────────────────────────

def new_uuid() -> uuid.UUID:
    return uuid.uuid4()


def strip_prefix(s: str, prefix: str) -> uuid.UUID:
    return uuid.UUID(s.replace(prefix, "", 1))


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


# ── マスタ参照テーブル (DB から一括ロード) ─────────────────────────────────────

def load_lookup_maps(session: Session) -> tuple[dict, dict, dict]:
    """
    Returns:
      product_code_to_uuid: {"PM0001": UUID, ...}
      unit_canonical_to_uuid: {"Pack": UUID, ...}
      cond_canonical_to_uuid: {"Sealed box": UUID, ...}
    """
    prod_rows = session.execute(text("SELECT code, id FROM tcg_products")).fetchall()
    product_code_to_uuid = {row[0]: uuid.UUID(str(row[1])) for row in prod_rows}

    unit_rows = session.execute(text("SELECT canonical, id FROM units")).fetchall()
    unit_canonical_to_uuid = {row[0]: uuid.UUID(str(row[1])) for row in unit_rows}

    cond_rows = session.execute(text("SELECT canonical, id FROM conditions")).fetchall()
    cond_canonical_to_uuid = {row[0]: uuid.UUID(str(row[1])) for row in cond_rows}

    return product_code_to_uuid, unit_canonical_to_uuid, cond_canonical_to_uuid


# ── compat engine 本体 ─────────────────────────────────────────────────────────

def run_compat_engine(session: Session) -> int:
    """analysis_results を生成して返す行数"""
    gemini = json.loads(GEMINI_FILE.read_text())

    product_code_to_uuid, unit_canonical_to_uuid, cond_canonical_to_uuid = \
        load_lookup_maps(session)

    inserted = 0
    for item in gemini:
        ei_raw = item["extraction_item_id"]
        ei_uuid = strip_prefix(ei_raw, "EIV2-")

        sys_v = item.get("system", {})
        gem_v = item.get("gemini", {})
        ri    = item.get("review_issues", [])

        # --- product_id FK ---
        pid_code = sys_v.get("product_id", "") or ""
        product_uuid = product_code_to_uuid.get(pid_code) if pid_code else None
        pid_resolved = sys_v.get("pid_resolved", "NO") == "YES"
        pid_basis    = sys_v.get("pid_basis") or None

        # --- unit FK ---
        unit_canonical = sys_v.get("unit") or None
        unit_uuid = (unit_canonical_to_uuid.get(unit_canonical)
                     if unit_canonical else None)
        unit_resolved = sys_v.get("unit_resolved", "NO") == "YES"

        # --- condition FK ---
        cond_canonical = sys_v.get("condition") or None
        cond_uuid = (cond_canonical_to_uuid.get(cond_canonical)
                     if cond_canonical else None)

        # --- quantity / price ---
        quantity_normalized = parse_qty(gem_v.get("quantity"))
        price_normalized    = parse_price(gem_v.get("price"))

        # --- needs_review / review_reasons ---
        needs_review   = bool(ri)
        review_reasons = json.dumps(ri, ensure_ascii=False) if ri else None

        # --- note / status / exclusion ---
        note_ja   = sys_v.get("note") or None
        status    = sys_v.get("status") or None
        exclusion = sys_v.get("exclusion") or None

        ar = AnalysisResult(
            id=new_uuid(),
            extraction_item_id=ei_uuid,
            product_id=product_uuid,
            pid_resolved=pid_resolved,
            pid_basis=pid_basis,
            unit_id=unit_uuid,
            unit_canonical=unit_canonical,
            unit_resolved=unit_resolved,
            condition_id=cond_uuid,
            condition_canonical=cond_canonical,
            quantity_normalized=quantity_normalized,
            price_normalized=price_normalized,
            note_ja=note_ja,
            status=status,
            exclusion=exclusion,
            needs_review=needs_review,
            review_reasons=review_reasons,
            engine_version=ENGINE_VERSION,
        )
        session.add(ar)
        inserted += 1

    session.flush()
    return inserted


# ── Phase 3 確認クエリ ─────────────────────────────────────────────────────────

def phase3_verify(session: Session):
    total       = session.execute(text("SELECT COUNT(*) FROM analysis_results")).scalar()
    needs_rev   = session.execute(text("SELECT COUNT(*) FROM analysis_results WHERE needs_review")).scalar()
    pid_unres   = session.execute(text("SELECT COUNT(*) FROM analysis_results WHERE NOT pid_resolved")).scalar()
    unit_unres  = session.execute(text("SELECT COUNT(*) FROM analysis_results WHERE NOT unit_resolved")).scalar()
    sp0023      = session.execute(text("""
        SELECT COUNT(*) FROM analysis_results ar
        JOIN extraction_items ei ON ei.id = ar.extraction_item_id
        JOIN extraction_jobs  ej ON ej.id = ei.extraction_job_id
        JOIN source_messages  sm ON sm.id = ej.source_message_id
        JOIN supplier_channels sc ON sc.id = sm.supplier_channel_id
        JOIN tcg_suppliers s ON s.id = sc.supplier_id
        WHERE s.code = 'SP0023'
    """)).scalar()

    EXPECTED = {
        "analysis_results total": (total, 1626),
        "needs_review=TRUE":       (needs_rev, 1394),
        "pid_unresolved":          (pid_unres, 344),
        "unit_unresolved":         (unit_unres, 528),
        "SP0023 items":            (sp0023, 198),
    }

    print("\n" + "=" * 60)
    print("Phase 3 Verification (compat-v1)")
    print("=" * 60)
    all_ok = True
    for label, (actual, expected) in EXPECTED.items():
        status = "OK" if actual == expected else "MISMATCH"
        if actual != expected:
            all_ok = False
        print(f"  {label:<30} actual={actual:>6}  expected={expected:>6}  {status}")
    print("=" * 60)
    if all_ok:
        print("  → Phase 3 PASS")
    else:
        print("  → Phase 3 FAIL")
    return all_ok


# ── main ───────────────────────────────────────────────────────────────────────

def main():
    print("MIG-02 Phase 3 Compat Engine 開始")
    print(f"  DB     : {DB_URL}")
    print(f"  GEMINI : {GEMINI_FILE}")
    print(f"  engine_version: {ENGINE_VERSION}")

    with Session(engine) as session:
        with session.begin():
            n = run_compat_engine(session)
            print(f"  → {n} 行を analysis_results に挿入")
            ok = phase3_verify(session)

    if ok:
        print("\n✅ Phase 3 PASS — compat engine 完了")
    else:
        print("\n❌ Phase 3 FAIL")
        sys.exit(1)


if __name__ == "__main__":
    main()
