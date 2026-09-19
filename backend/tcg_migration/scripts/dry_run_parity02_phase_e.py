"""
TCG PARITY-02 Phase E 測定スクリプト（read-only dry-run）。

Phase D 統合後の analyze_extraction_job フルパイプラインを
メモリ上でシミュレーションし、DB への書き込みを一切行わない。

出力項目:
  - pid / unit / condition / status / note の解決率と分布
  - GAS 実測値との並列比較（参考値）
  - 未解決の内訳（pid_basis NONE/MULTI / unit_resolved=FALSE の理由別）
  - unit_basis 分布（per-row + E3a/E3b/E4 後）
  - E2 未実装の影響（unit_resolved=FALSE 行のうち価格帯で解決しうる件数）

使用方法:
  export TCG_DB_PROD_URL="postgresql+psycopg2://user:pass@host:5432/db"
  cd backend
  python -m tcg_migration.scripts.dry_run_parity02_phase_e

  # extraction_job_id を指定する場合
  python -m tcg_migration.scripts.dry_run_parity02_phase_e <extraction_job_id>

VPS 上 (docker exec):
  docker exec -e DATABASE_URL="..." -w /app astro-webapp-backend-1 \\
    python -m tcg_migration.scripts.dry_run_parity02_phase_e

終了コード:
  0 = 正常完了
  1 = エラー

GAS 実測値（2026-09-01 実測、E3a+E5 適用後）:
  condition_canonical 分布: FLAG_SINGLE=764, Sealed box=468, Case=217,
    No shrink box=71, Searched pack=61, Damaged case=17, Unsearched pack=12,
    Damaged sealed box=11, Opened box=5 → 合計 1626
  E3a NAME_RECOVERY: 11行
"""
from __future__ import annotations

import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.services.tcg_analyzer_svc import (
    apply_field_normalization,
    build_note_ja,
    filter_product_codes_by_unit_kubun,
    load_condition_entries,
    load_lookup_maps,
    load_normalization_rules,
    load_note_master,
    load_product_keywords,
    load_product_kubun_type_map,
    load_status_master,
    match_pid_name_first,
    resolve_condition_v2,
    resolve_status_v2,
    resolve_unit_v2,
)
from app.services.tcg_unit_recovery_svc import (
    _CASE_TERM_NFKC,
    E3A_MAX_RECOVER,
    build_unit_recovery_terms,
    find_term,
    unit_recovery_norm,
)

TCG_SCHEMA = "tenant_004"

# GAS 実測値（参考・一致は求めない）
GAS_CONDITION_DIST = {
    "FLAG_SINGLE": 764,
    "Sealed box": 468,
    "Case": 217,
    "No shrink box": 71,
    "Searched pack": 61,
    "Damaged case": 17,
    "Unsearched pack": 12,
    "Damaged sealed box": 11,
    "Opened box": 5,
}
GAS_TOTAL = sum(GAS_CONDITION_DIST.values())  # 1626
GAS_E3A_RECOVERED = 11
GAS_PID_RESOLVED = None   # GAS 非公開（分かれば更新）
GAS_STATUS_EXCLUDED = None  # 未実測


@dataclass
class ItemResult:
    item_id: str
    raw_product_name: str
    raw_unit: str
    raw_state: str
    raw_memo: str
    raw_price: Optional[float]

    # per-row 解決結果
    pid_resolved: bool = False
    pid_basis: str = ""
    multi_candidate: bool = False
    unit_canonical: Optional[str] = None
    unit_resolved: bool = False
    condition_canonical: Optional[str] = None
    condition_basis: str = ""
    note_ja: Optional[str] = None
    status: str = "active"
    exclusion: Optional[str] = None

    # 後処理フラグ
    unit_basis: Optional[str] = None  # NAME_RECOVERY:* / UNIT_UNRESOLVED / COND_INFERRED / None


def _load_extraction_items(session, extraction_job_id: Optional[str]) -> list[dict]:
    """extraction_items を全件または指定 job_id で取得"""
    if extraction_job_id:
        rows = session.execute(
            text(
                f"""
                SELECT id, raw_product_name, raw_quantity, raw_price, raw_unit, raw_state,
                       raw_memo, extraction_job_id
                FROM {TCG_SCHEMA}.extraction_items
                WHERE extraction_job_id = :job_id
                ORDER BY line_start, id
                """
            ),
            {"job_id": extraction_job_id},
        ).fetchall()
    else:
        # 最新 job を自動選択
        latest = session.execute(
            text(
                f"""
                SELECT id FROM {TCG_SCHEMA}.extraction_jobs
                ORDER BY created_at DESC LIMIT 1
                """
            )
        ).fetchone()
        if not latest:
            print("ERROR: extraction_jobs が空です", file=sys.stderr)
            sys.exit(1)
        job_id = str(latest[0])
        print(f"[auto-select] extraction_job_id = {job_id}")
        rows = session.execute(
            text(
                f"""
                SELECT id, raw_product_name, raw_quantity, raw_price, raw_unit, raw_state,
                       raw_memo, extraction_job_id
                FROM {TCG_SCHEMA}.extraction_items
                WHERE extraction_job_id = :job_id
                ORDER BY line_start, id
                """
            ),
            {"job_id": job_id},
        ).fetchall()

    return [
        {
            "id": str(r[0]),
            "raw_product_name": r[1] or "",
            "raw_quantity": r[2],
            "raw_price": float(r[3]) if r[3] is not None else None,
            "raw_unit": r[4] or "",
            "raw_state": r[5] or "",
            "raw_memo": r[6] or "",
            "job_id": str(r[7]),
        }
        for r in rows
    ]


def _simulate_e3a(
    results: list[ItemResult],
    session,
    product_id_map: dict,  # item_id → product_id (UUID)
    japanese_title_map: dict,  # product_id → japanese_title
) -> list[str]:
    """E3a: 商品名から unit 復旧 — in-memory シミュレーション。
    回収された item_id リストを返す。"""
    unit_terms = build_unit_recovery_terms()
    if not unit_terms:
        return []

    recovered_ids = []
    count = 0

    for r in results:
        if r.unit_resolved:
            continue
        if r.raw_unit.strip():
            continue
        if not r.pid_resolved:
            continue
        if not r.raw_product_name.strip():
            continue

        matched = find_term(r.raw_product_name, unit_terms)
        if not matched:
            continue

        norm_pn = unit_recovery_norm(r.raw_product_name)
        norm_term = unit_recovery_norm(matched["term"])
        if norm_term and not norm_pn.endswith(norm_term):
            continue

        if norm_term == _CASE_TERM_NFKC:
            pre_pn = norm_pn[: len(norm_pn) - len(norm_term)]
            if pre_pn and not re.search(r"[\s\u3000]$", pre_pn):
                continue

        product_id = product_id_map.get(r.item_id)
        if product_id:
            jp_title = japanese_title_map.get(str(product_id), "")
            if jp_title:
                norm_jp = unit_recovery_norm(jp_title)
                if norm_term in norm_jp:
                    continue

        # 回収確定
        r.unit_canonical = matched["canonical"]
        r.unit_resolved = True
        r.unit_basis = f"NAME_RECOVERY:{matched['term']}"
        count += 1
        recovered_ids.append(r.item_id)

        if count >= E3A_MAX_RECOVER:
            print(f"  [WARNING] E3a safety limit reached ({E3A_MAX_RECOVER})", file=sys.stderr)
            break

    return recovered_ids


def _simulate_e5(
    results: list[ItemResult],
    recovered_ids: set[str],
    cond_entries,
    cond_canonical_to_uuid,
) -> int:
    """E5: NAME_RECOVERY 行の condition 再計算 — in-memory シミュレーション"""
    target_basis = "R4:単位既定:単位不明"
    changed = 0

    id_to_result = {r.item_id: r for r in results}
    for item_id in recovered_ids:
        r = id_to_result.get(item_id)
        if not r or r.condition_basis != target_basis:
            continue

        # unit kubun の取得（unit_basis から term を取得し unit info を引く）
        # r.unit_canonical が判明しているので load_lookup_maps 結果から kubun を取得
        # ここでは簡易: unit_canonical → kubun はすでに resolve_unit_v2 済み
        # E5 は condition_basis='R4:単位既定:単位不明' のみ対象なので
        # 元の raw_state + raw_product_name + 新 kubun で再解決
        # ※ kubun は unit_basis から取得できないため、unit_canonical をそのまま渡す
        # 実際の E5 は unit kubun を使うが、dry-run では近似として unit_canonical を使用
        new_canonical, _, new_basis = resolve_condition_v2(
            r.raw_state,
            r.raw_product_name,
            r.unit_canonical or "",  # kubun 代わりに canonical で近似
            cond_entries,
            cond_canonical_to_uuid,
        )
        if new_canonical != r.condition_canonical:
            r.condition_canonical = new_canonical
            r.condition_basis = new_basis
            changed += 1

    return changed


def _simulate_e2_impact(results: list[ItemResult], session) -> dict:
    """E2 未実装の影響: unit_resolved=FALSE 行のうち価格帯で解決しうる件数を推定"""
    # tcg_unit_evidence_rules からルールを取得
    try:
        evidence_rows = session.execute(
            text(
                f"""
                SELECT rule_type, price_min, price_max, unit_id, canonical
                FROM {TCG_SCHEMA}.tcg_unit_evidence_rules
                WHERE enabled = TRUE
                ORDER BY priority ASC
                """
            )
        ).fetchall()
    except Exception:
        return {"available": False, "reason": "tcg_unit_evidence_rules テーブルなし"}

    if not evidence_rows:
        return {"available": True, "rules": 0, "matchable": 0}

    # unit_resolved=FALSE かつ price があれば価格帯照合を試みる
    unresolved = [r for r in results if not r.unit_resolved and r.raw_price is not None]
    matchable = 0
    for r in unresolved:
        price = r.raw_price
        for rule in evidence_rows:
            rule_type, price_min, price_max, unit_id, canonical = rule
            if rule_type == "PRICE_BAND":
                if (price_min is None or price >= price_min) and (
                    price_max is None or price <= price_max
                ):
                    matchable += 1
                    break

    return {
        "available": True,
        "rules": len(evidence_rows),
        "unresolved_with_price": len(unresolved),
        "matchable": matchable,
    }


def run_phase_e_simulation(session, extraction_job_id: Optional[str] = None) -> dict:
    """Phase E 全シミュレーション実行"""

    print("=== TCG PARITY-02 Phase E 測定 (dry-run) ===\n")

    # マスタロード
    print("[1/6] ルックアップマップをロード...")
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
    norm_rules = load_normalization_rules(session)
    note_entries = load_note_master(session)
    status_entries = load_status_master(session)

    print(
        f"  products={len(product_codes)}, norm_rules={sum(len(v) for v in norm_rules.values())}, "
        f"note_entries={len(note_entries)}, status_entries={len(status_entries)}"
    )

    # extraction_items ロード
    print("[2/6] extraction_items をロード...")
    items = _load_extraction_items(session, extraction_job_id)
    print(f"  {len(items)} 件")

    if not items:
        print("ERROR: extraction_items が空です", file=sys.stderr)
        sys.exit(1)

    job_id = items[0]["job_id"]

    # E3a 用: product_id マップ（item_id → product_id）
    pid_rows = session.execute(
        text(
            f"""
            SELECT ei.id, ar.product_id
            FROM {TCG_SCHEMA}.extraction_items ei
            LEFT JOIN {TCG_SCHEMA}.analysis_results ar ON ar.extraction_item_id = ei.id
            WHERE ei.extraction_job_id = :job_id
            """
        ),
        {"job_id": job_id},
    ).fetchall()
    product_id_map = {str(r[0]): str(r[1]) if r[1] else None for r in pid_rows}

    # japanese_title マップ
    jp_rows = session.execute(
        text(f"SELECT id, japanese_title FROM {TCG_SCHEMA}.tcg_products")
    ).fetchall()
    japanese_title_map = {str(r[0]): r[1] or "" for r in jp_rows}

    # per-row シミュレーション
    print("[3/6] per-row 解析シミュレーション...")
    results: list[ItemResult] = []

    pid_basis_counter: dict[str, int] = defaultdict(int)

    for item in items:
        raw_pn = item["raw_product_name"]
        raw_unit = item["raw_unit"]
        raw_state = item["raw_state"]
        raw_memo = item["raw_memo"]
        raw_price = item["raw_price"]

        # C-1: 正規化
        norm_pn = apply_field_normalization(raw_pn, norm_rules.get("PRODUCT_NAME", []))
        norm_unit = apply_field_normalization(raw_unit, norm_rules.get("UNIT", []))
        norm_cond = apply_field_normalization(raw_state, norm_rules.get("CONDITION", []))
        norm_status = apply_field_normalization(raw_state, norm_rules.get("STATUS", []))
        norm_memo = apply_field_normalization(raw_memo, norm_rules.get("NOTE", []))

        # 単位解決
        unit_canonical, kubun, unit_resolved = resolve_unit_v2(norm_unit, unit_alias_to_info)
        filtered_codes = filter_product_codes_by_unit_kubun(
            product_codes, kubun, product_code_to_kubun_type
        )

        # 商品照合
        matched_code, pid_basis, pid_resolved, candidates = match_pid_name_first(
            norm_pn, filtered_codes, search_kw, exclude_kw
        )
        pid_basis_counter[pid_basis] += 1

        # 状態解決
        condition_canonical, _, condition_basis_str = resolve_condition_v2(
            norm_cond, norm_pn, kubun, cond_entries, cond_canonical_to_uuid
        )

        # 注記生成
        note_ja = build_note_ja(norm_memo, note_entries)

        # ステータス解決
        status_val, exclusion_val = resolve_status_v2(norm_status, status_entries)

        r = ItemResult(
            item_id=item["id"],
            raw_product_name=raw_pn,
            raw_unit=raw_unit,
            raw_state=raw_state,
            raw_memo=raw_memo,
            raw_price=raw_price,
            pid_resolved=pid_resolved,
            pid_basis=pid_basis,
            multi_candidate=len(candidates) > 1,
            unit_canonical=unit_canonical,
            unit_resolved=unit_resolved,
            condition_canonical=condition_canonical,
            condition_basis=condition_basis_str,
            note_ja=note_ja,
            status=status_val,
            exclusion=exclusion_val,
        )
        results.append(r)

    # E3a シミュレーション
    print("[4/6] E3a (NAME_RECOVERY) シミュレーション...")
    recovered_ids = _simulate_e3a(results, session, product_id_map, japanese_title_map)
    print(f"  E3a recovered: {len(recovered_ids)} 行")

    # E5 シミュレーション
    print("[5/6] E5 (condition 再計算) シミュレーション...")
    e5_changed = _simulate_e5(
        results, set(recovered_ids), cond_entries, cond_canonical_to_uuid
    )
    print(f"  E5 changed: {e5_changed} 行")

    # E3b: unit_resolved=FALSE に UNIT_UNRESOLVED フラグ
    for r in results:
        if not r.unit_resolved and r.unit_basis is None:
            r.unit_basis = "UNIT_UNRESOLVED"

    # E4: condition_canonical から unit 逆引き（現データ 0 件想定・省略）

    # E2 影響推定
    print("[6/6] E2 未実装の影響を推定...")
    e2_impact = _simulate_e2_impact(results, session)

    return {
        "total": len(results),
        "results": results,
        "e3a_recovered": len(recovered_ids),
        "e5_changed": e5_changed,
        "e2_impact": e2_impact,
        "pid_basis_counter": dict(pid_basis_counter),
    }


def print_report(data: dict) -> None:
    total = data["total"]
    results = data["results"]

    print()
    print("=" * 70)
    print("  TCG PARITY-02 Phase E — 測定レポート")
    print("=" * 70)
    print(f"  対象件数: {total} 件")
    print()

    # --- PID 解決率 ---
    pid_ok = sum(1 for r in results if r.pid_resolved)
    pid_multi = sum(1 for r in results if r.multi_candidate)
    pid_none = sum(1 for r in results if not r.pid_resolved and not r.multi_candidate)
    print("--- PID 解決 ---")
    print(f"  resolved:      {pid_ok:5d} / {total}  ({pid_ok/total*100:.1f}%)")
    print(f"  multi_cand:    {pid_multi:5d}  (未解決の要因: 候補複数)")
    print(f"  unresolved:    {pid_none:5d}  (候補なし)")
    if GAS_PID_RESOLVED is not None:
        print(f"  GAS 実測:      {GAS_PID_RESOLVED:5d}  (参考)")
    print()

    # --- UNIT 解決率 ---
    unit_ok = sum(1 for r in results if r.unit_resolved)
    unit_unresolved = total - unit_ok
    unit_basis_dist: dict[str, int] = defaultdict(int)
    for r in results:
        basis = r.unit_basis or ("resolved" if r.unit_resolved else "UNIT_UNRESOLVED")
        if r.unit_resolved and r.unit_basis is None:
            basis = "per-row"
        unit_basis_dist[basis] += 1

    print("--- UNIT 解決 ---")
    print(f"  resolved:      {unit_ok:5d} / {total}  ({unit_ok/total*100:.1f}%)")
    print(f"  unresolved:    {unit_unresolved:5d}")
    print()
    print("  unit_basis 分布:")
    for basis, cnt in sorted(unit_basis_dist.items(), key=lambda x: -x[1]):
        marker = " (E3a)" if "NAME_RECOVERY" in basis else ""
        print(f"    {basis:<35} {cnt:5d}{marker}")
    print()
    print(f"  E3a NAME_RECOVERY 合計: {data['e3a_recovered']:5d}")
    print(f"  GAS E3a 実測:           {GAS_E3A_RECOVERED:5d}  (参考)")
    print()

    # --- CONDITION 分布 ---
    cond_dist: dict[str, int] = defaultdict(int)
    for r in results:
        cond_dist[r.condition_canonical or "NULL"] += 1

    print("--- CONDITION 分布 (Python vs GAS) ---")
    all_keys = sorted(
        set(list(cond_dist.keys()) + list(GAS_CONDITION_DIST.keys())),
        key=lambda k: -(cond_dist.get(k, 0)),
    )
    print(f"  {'condition_canonical':<25} {'Python':>8} {'GAS':>8} {'diff':>8}")
    print(f"  {'-'*25} {'-'*8} {'-'*8} {'-'*8}")
    py_total_cond = 0
    for k in all_keys:
        py = cond_dist.get(k, 0)
        gas = GAS_CONDITION_DIST.get(k, 0)
        diff = py - gas
        py_total_cond += py
        marker = " ✅" if diff == 0 and gas > 0 else (" ❌" if diff != 0 else "")
        print(f"  {k:<25} {py:>8} {gas:>8} {diff:>+8}{marker}")
    print(f"  {'合計':<25} {py_total_cond:>8} {GAS_TOTAL:>8} {py_total_cond - GAS_TOTAL:>+8}")
    if py_total_cond == GAS_TOTAL:
        match_count = sum(1 for k in GAS_CONDITION_DIST if cond_dist.get(k, 0) == GAS_CONDITION_DIST[k])
        print(f"  一致率: {match_count}/{len(GAS_CONDITION_DIST)} condition 完全一致")
    print()

    # --- STATUS / NOTE ---
    status_dist: dict[str, int] = defaultdict(int)
    for r in results:
        status_dist[r.status or "NULL"] += 1
    excluded = sum(1 for r in results if r.exclusion == "excluded")
    noted = sum(1 for r in results if r.note_ja is not None)

    print("--- STATUS / NOTE ---")
    print("  status 分布:")
    for k, cnt in sorted(status_dist.items(), key=lambda x: -x[1]):
        print(f"    {k:<20} {cnt:5d}")
    print(f"  exclusion='excluded': {excluded:5d}")
    print(f"  note_ja IS NOT NULL:  {noted:5d}")
    if GAS_STATUS_EXCLUDED is not None:
        print(f"  GAS status excluded:  {GAS_STATUS_EXCLUDED:5d}  (参考)")
    print()

    # --- E2 未実装の影響 ---
    e2 = data["e2_impact"]
    print("--- E2 未実装の影響（価格帯からの unit 推定）---")
    if not e2["available"]:
        print(f"  {e2['reason']}")
    else:
        print(f"  tcg_unit_evidence_rules: {e2['rules']} 件")
        print(f"  unit_resolved=FALSE 行:  {unit_unresolved}")
        print(f"    うち price あり:       {e2.get('unresolved_with_price', 'N/A')}")
        print(f"    価格帯マッチあり:      {e2.get('matchable', 0)}  ← E2 で解決しうる行数")
    print()

    print("=" * 70)


def main() -> int:
    db_url = os.environ.get("TCG_DB_PROD_URL") or os.environ.get("DATABASE_URL")
    if not db_url:
        print(
            "ERROR: TCG_DB_PROD_URL or DATABASE_URL must be set",
            file=sys.stderr,
        )
        return 1

    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    extraction_job_id = sys.argv[1] if len(sys.argv) > 1 else None

    engine = create_engine(db_url, echo=False)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        try:
            data = run_phase_e_simulation(session, extraction_job_id)
            print_report(data)
        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            return 1
        finally:
            session.rollback()  # dry-run: 万一の書き込みも rollback

    return 0


if __name__ == "__main__":
    sys.exit(main())
