"""
TCG E3a + E5: 単位復旧・状態再計算 (dry-run 専用)。

GAS AnalysisV2UnitRecovery.gs / AnalysisV2ConditionRecalc.gs の 1:1 移植。
DB への書き込みは行わない（dry-run モード）。

E3a (recoverUnitFromProductName):
  商品名末尾の単位マスタ語から unit を復旧する。
  GAS: AnalysisV2UnitRecovery.gs:134-276

E5 (recalcConditionFromResolvedUnit):
  NAME_RECOVERY 行の condition を再計算する。
  GAS: AnalysisV2ConditionRecalc.gs:217-276

公開関数:
  run_unit_recovery_dry_run(session, tenant_schema) -> dict
"""
from __future__ import annotations

import logging
import re
import unicodedata
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.tcg_analyzer_svc import (
    load_condition_entries,
    load_lookup_maps,
    resolve_condition_v2,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# 安全装置上限
E3A_MAX_RECOVER = 100
E5_MAX_ROWS = 200

# word-boundary が必要な検索語（ct/CT/Ct は他のアルファベット語の一部になりうる）
# GAS: AnalysisV2UnitRecovery.gs:25
_CT_TERMS: set[str] = {"ct", "CT", "Ct"}

# GAS: AnalysisV2UnitRecovery.gs:224 — 'ケース' (U+30B1 U+30FC U+30B9)
_CASE_TERM_NFKC = "\u30b1\u30fc\u30b9"

# 全角英字範囲 (GAS regex: \uff41-\uff5a\uff21-\uff3a)
# NFKC 正規化後は半角化されるため通常は不要だが、GAS との互換で lookbehind に含める
_CT_BOUNDARY_RE_TEMPLATE = (
    r"(?<![a-zA-Z\uff41-\uff5a\uff21-\uff3a])"
    r"{term}"
    r"(?![a-zA-Z\uff41-\uff5a\uff21-\uff3a])"
)


# ---------------------------------------------------------------------------
# Unit Master (hardcoded from GAS _UNIT_MASTER_ROWS_)
# ---------------------------------------------------------------------------

# 全 8 ユニット (status='有効')
# GAS: 00_Constants.gs / investigate2.gs:5454 _UNIT_MASTER_ROWS_
_UNIT_MASTER_ROWS = [
    {
        "unit_id": "UN0001",
        "canonical": "Case",
        "kubun": "箱系大",
        "aliases": "case,CASE,Case,carton,CARTON,Carton,ct,CT,Ct,カートン,ケース,ｶｰﾄﾝ,ｹｰｽ",
    },
    {
        "unit_id": "UN0002",
        "canonical": "Box",
        "kubun": "箱系",
        "aliases": "box,BOX,Box,ボックス,箱,ﾎﾞｯｸｽ",
    },
    {
        "unit_id": "UN0003",
        "canonical": "Pack",
        "kubun": "パック系",
        "aliases": "pack,PACK,Pack,パック,ﾊﾟｯｸ",
    },
    {
        "unit_id": "UN0004",
        "canonical": "Piece",
        "kubun": "枚系",
        "aliases": "piece,PIECE,Piece,pcs,PCS,Pcs,枚",
    },
    {
        "unit_id": "UN0005",
        "canonical": "Set",
        "kubun": "セット系",
        "aliases": "set,SET,Set,セット,ｾｯﾄ",
    },
    {
        "unit_id": "UN0006",
        "canonical": "本",
        "kubun": "除外",
        "aliases": "",
    },
    {
        "unit_id": "UN0007",
        "canonical": "点",
        "kubun": "数量専用",
        "aliases": "",
    },
    {
        "unit_id": "UN0008",
        "canonical": "個",
        "kubun": "条件つき",
        "aliases": "",
    },
]


# ---------------------------------------------------------------------------
# NFKC normalization
# ---------------------------------------------------------------------------


def unit_recovery_norm(s: Optional[str]) -> str:
    """
    NFKC 正規化 + trim。

    GAS 対照: AnalysisV2UnitRecovery.gs:30-32 unitRecoveryNorm_
      return String(s || '').normalize('NFKC').trim();
    """
    return unicodedata.normalize("NFKC", str(s or "")).strip()


# ---------------------------------------------------------------------------
# Build unit recovery terms (longest-first sorted)
# ---------------------------------------------------------------------------


def build_unit_recovery_terms() -> list[dict]:
    """
    単位マスタから検索語リストを構築する（長い順ソート済み）。

    GAS 対照: AnalysisV2UnitRecovery.gs:91-104 unitRecoveryBuildTerms_
      um.entries.forEach(entry => {
        var allTerms = [entry.canonical].concat(entry.aliases || []);
        allTerms.forEach(term => terms.push({term, unitId, canonical}));
      });
      terms.sort((a,b) => b.term.length - a.term.length);

    Returns:
      [{term, unit_id, canonical, kubun}] sorted by len(term) desc
    """
    terms: list[dict] = []
    for entry in _UNIT_MASTER_ROWS:
        all_terms = [entry["canonical"]]
        if entry["aliases"]:
            all_terms.extend(
                t.strip() for t in entry["aliases"].split(",") if t.strip()
            )
        for term in all_terms:
            term = str(term or "").strip()
            if not term:
                continue
            terms.append(
                {
                    "term": term,
                    "unit_id": entry["unit_id"],
                    "canonical": entry["canonical"],
                    "kubun": entry["kubun"],
                }
            )
    terms.sort(key=lambda x: len(x["term"]), reverse=True)
    return terms


# ---------------------------------------------------------------------------
# Find term in text (longest-match, with CT word-boundary)
# ---------------------------------------------------------------------------


def find_term(
    text_str: str, terms: list[dict]
) -> Optional[dict]:
    """
    テキスト内の単位マスタ語を最長一致で検索する。

    GAS 対照: AnalysisV2UnitRecovery.gs:40-59 unitRecoveryFindTerm_
      for each term:
        normTerm = NFKC(term)
        if CT_TERMS[normTerm]:
          regex word-boundary check
        else:
          simple indexOf

    Args:
      text_str: 検索対象テキスト（NFKC正規化前）
      terms: build_unit_recovery_terms() の戻り値

    Returns:
      matched {term, unit_id, canonical, kubun} or None
    """
    norm_text = unit_recovery_norm(text_str)
    for t in terms:
        norm_term = unit_recovery_norm(t["term"])
        if not norm_term:
            continue
        if norm_term in _CT_TERMS:
            # CT/ct/Ct — word-boundary regex
            escaped = re.escape(norm_term)
            pattern = _CT_BOUNDARY_RE_TEMPLATE.format(term=escaped)
            if re.search(pattern, norm_text):
                return t
        else:
            # simple indexOf
            if norm_term in norm_text:
                return t
    return None


# ---------------------------------------------------------------------------
# E3a: recover_unit_from_product_name (dry-run)
# ---------------------------------------------------------------------------


def recover_unit_from_product_name(
    session: Session,
    tenant_schema: str = "tenant_004",
) -> dict:
    """
    E3a: 商品名から単位を復旧する (dry-run — DB 書き込みなし)。

    GAS 対照: AnalysisV2UnitRecovery.gs:134-276 recoverUnitFromProductName

    Algorithm:
      1. unit_resolved = FALSE (NO)
      2. raw_unit = '' (empty)
      3. pid_resolved = TRUE (YES)
      4. product_name not empty
      5. find_term(product_name, terms) -> matched
      6. End-match: product_name must END WITH matched term (NFKC)
      7. 'ケース' special: preceding char must be whitespace
      8. A-2 exclusion: if product in master and jpTitle contains term -> skip
      9. -> RECOVER

    Returns:
      {
        success: bool,
        updated_count: int,
        aborted: bool,
        message: str,
        details: [{item_id, product_name, term, unit_id, canonical, kubun}],
      }
    """
    unit_terms = build_unit_recovery_terms()
    if not unit_terms:
        return {
            "success": False,
            "updated_count": 0,
            "aborted": False,
            "message": "unit master has no active entries",
            "details": [],
        }

    # Load analysis_results joined with extraction_items and tcg_products
    rows = session.execute(
        text(
            f"""
            SELECT
                ar.id                AS ar_id,
                ar.extraction_item_id,
                ar.unit_resolved,
                ar.pid_resolved,
                ar.product_id,
                ei.raw_unit,
                ei.raw_product_name,
                tp.code              AS product_code,
                tp.japanese_title
            FROM {tenant_schema}.analysis_results ar
            JOIN {tenant_schema}.extraction_items ei
                ON ei.id = ar.extraction_item_id
            LEFT JOIN {tenant_schema}.tcg_products tp
                ON tp.id = ar.product_id
            ORDER BY ar.id
            """
        )
    ).fetchall()

    details: list[dict] = []

    for row in rows:
        (
            ar_id,
            extraction_item_id,
            unit_resolved,
            pid_resolved,
            product_id,
            raw_unit,
            raw_product_name,
            product_code,
            japanese_title,
        ) = row

        # Step 1: unit_resolved must be False (NO)
        if unit_resolved:
            continue

        # Step 2: raw_unit must be empty
        raw_unit_str = str(raw_unit or "").strip()
        if raw_unit_str:
            continue

        # Step 3: pid_resolved must be True (YES)
        if not pid_resolved:
            continue

        # Step 4: product_name must not be empty
        product_name = str(raw_product_name or "").strip()
        if not product_name:
            continue

        # Step 5: find term in product_name (longest-match)
        matched = find_term(product_name, unit_terms)
        if not matched:
            continue

        # Step 6: End-match check
        # GAS: AnalysisV2UnitRecovery.gs:218-220
        norm_pn = unit_recovery_norm(product_name)
        norm_term = unit_recovery_norm(matched["term"])
        if norm_term and not norm_pn.endswith(norm_term):
            continue

        # Step 7: 'ケース' special — preceding char must be whitespace or start of string
        # GAS: AnalysisV2UnitRecovery.gs:224-227
        if norm_term == _CASE_TERM_NFKC:
            pre_pn = norm_pn[: len(norm_pn) - len(norm_term)]
            if pre_pn and not re.search(r"[\s\u3000]$", pre_pn):
                continue

        # Step 8: A-2 exclusion — product master title contains the term
        # GAS: AnalysisV2UnitRecovery.gs:230-237
        if product_id and japanese_title:
            norm_jp = unit_recovery_norm(japanese_title)
            if norm_term in norm_jp:
                continue
            # Note: enTitle check omitted — DB has no english_title column

        details.append(
            {
                "ar_id": str(ar_id),
                "extraction_item_id": str(extraction_item_id),
                "product_name": product_name,
                "product_code": product_code or "",
                "term": matched["term"],
                "unit_id": matched["unit_id"],
                "canonical": matched["canonical"],
                "kubun": matched["kubun"],
                "unit_basis": f"NAME_RECOVERY:{matched['term']}",
            }
        )

    # Safety limit
    if len(details) > E3A_MAX_RECOVER:
        return {
            "success": False,
            "updated_count": 0,
            "aborted": True,
            "message": (
                f"Safety abort: {len(details)} rows would be recovered "
                f"(limit: {E3A_MAX_RECOVER})"
            ),
            "details": details,
        }

    return {
        "success": True,
        "updated_count": len(details),
        "aborted": False,
        "message": f"{len(details)} rows would be recovered",
        "details": details,
    }


# ---------------------------------------------------------------------------
# E5: recalc_condition_from_recovered_unit (dry-run)
# ---------------------------------------------------------------------------


def recalc_condition_from_recovered_unit(
    e3a_details: list[dict],
    session: Session,
    tenant_schema: str = "tenant_004",
) -> dict:
    """
    E5: NAME_RECOVERY 行の condition を再計算する (dry-run — DB 書き込みなし)。

    GAS 対照: AnalysisV2ConditionRecalc.gs:217-276 recalcConditionFromResolvedUnit

    対象:
      unit_basis starts with 'NAME_RECOVERY:'
      AND condition_basis = 'R4:単位既定:単位不明'

    Args:
      e3a_details: E3a の結果 (details リスト)。
                   各要素は {ar_id, unit_id, canonical, kubun, unit_basis, ...}
      session: SQLAlchemy Session
      tenant_schema: テナントスキーマ名

    Returns:
      {
        success: bool,
        target_count: int,
        changed_count: int,
        aborted: bool,
        message: str,
        changes: [{ar_id, unit_canonical, old_condition, new_condition, new_basis}],
        condition_breakdown: {canonical: count},
      }
    """
    if not e3a_details:
        return {
            "success": True,
            "target_count": 0,
            "changed_count": 0,
            "aborted": False,
            "message": "No E3a results to recalculate",
            "changes": [],
            "condition_breakdown": {},
        }

    # Load condition entries and lookup maps for resolve_condition_v2
    (
        _product_code_to_uuid,
        _unit_alias_to_canonical,
        _unit_canonical_to_uuid,
        _cond_alias_to_canonical,
        cond_canonical_to_uuid,
        _unit_alias_to_info,
    ) = load_lookup_maps(session)
    cond_entries = load_condition_entries(session)

    # Collect E3a ar_ids for which we need current condition_basis
    ar_ids = [d["ar_id"] for d in e3a_details]

    # Read current condition_basis for these rows
    if ar_ids:
        placeholders = ", ".join(f":id_{i}" for i in range(len(ar_ids)))
        params = {f"id_{i}": ar_id for i, ar_id in enumerate(ar_ids)}
        current_rows = session.execute(
            text(
                f"""
                SELECT ar.id, ar.condition_basis, ar.condition_canonical,
                       ei.raw_state, ei.raw_product_name
                FROM {tenant_schema}.analysis_results ar
                JOIN {tenant_schema}.extraction_items ei
                    ON ei.id = ar.extraction_item_id
                WHERE ar.id IN ({placeholders})
                """
            ),
            params,
        ).fetchall()
    else:
        current_rows = []

    current_map: dict[str, dict] = {}
    for row in current_rows:
        current_map[str(row[0])] = {
            "condition_basis": str(row[1] or ""),
            "condition_canonical": str(row[2] or ""),
            "raw_state": str(row[3] or ""),
            "raw_product_name": str(row[4] or ""),
        }

    # E3a detail -> kubun map for quick lookup
    e3a_map: dict[str, dict] = {d["ar_id"]: d for d in e3a_details}

    # Target: NAME_RECOVERY basis AND R4:単位既定:単位不明 condition_basis
    target_basis = "R4:単位既定:単位不明"
    changes: list[dict] = []
    condition_breakdown: dict[str, int] = {}

    for ar_id, detail in e3a_map.items():
        current = current_map.get(ar_id)
        if not current:
            continue

        # Filter: must have R4:単位既定:単位不明 as current condition_basis
        if current["condition_basis"] != target_basis:
            continue

        # Recalculate condition using recovered unit's kubun
        kubun = detail["kubun"]
        raw_state = current["raw_state"]
        raw_product_name = current["raw_product_name"]

        new_canonical, new_cond_id, new_basis = resolve_condition_v2(
            raw_state,
            raw_product_name,
            kubun,
            cond_entries,
            cond_canonical_to_uuid,
        )

        # Track in breakdown
        bk_key = new_canonical or "(empty)"
        condition_breakdown[bk_key] = condition_breakdown.get(bk_key, 0) + 1

        changed = new_canonical != current["condition_canonical"]
        if changed:
            changes.append(
                {
                    "ar_id": ar_id,
                    "unit_canonical": detail["canonical"],
                    "old_condition": current["condition_canonical"],
                    "new_condition": new_canonical,
                    "new_cond_id": new_cond_id,
                    "new_basis": new_basis,
                }
            )

    # Safety limit
    target_count = len(
        [
            ar_id
            for ar_id in e3a_map
            if current_map.get(ar_id, {}).get("condition_basis") == target_basis
        ]
    )
    if target_count > E5_MAX_ROWS:
        return {
            "success": False,
            "target_count": target_count,
            "changed_count": 0,
            "aborted": True,
            "message": (
                f"Safety abort: {target_count} target rows "
                f"(limit: {E5_MAX_ROWS})"
            ),
            "changes": [],
            "condition_breakdown": condition_breakdown,
        }

    return {
        "success": True,
        "target_count": target_count,
        "changed_count": len(changes),
        "aborted": False,
        "message": (
            f"E5 complete: {target_count} targets, "
            f"{len(changes)} would change"
        ),
        "changes": changes,
        "condition_breakdown": condition_breakdown,
    }


# ---------------------------------------------------------------------------
# Dry-run entry point
# ---------------------------------------------------------------------------


def run_unit_recovery_dry_run(
    session: Session,
    tenant_schema: str = "tenant_004",
) -> dict:
    """
    E3a + E5 dry-run: DB 書き込みなし。

    1. E3a: 商品名から unit 復旧候補を収集
    2. E5: NAME_RECOVERY 行の condition 再計算
    3. 結果の分布サマリーを返す

    Returns:
      {
        e3a: {success, updated_count, aborted, message, details},
        e5:  {success, target_count, changed_count, aborted, message, changes, condition_breakdown},
        summary: {
          name_recovery_count: int,
          name_recovery_by_term: {term: count},
          condition_distribution: {canonical: count},
        },
      }
    """
    # E3a
    e3a_result = recover_unit_from_product_name(session, tenant_schema)

    # E5 (pass E3a results)
    e5_result = recalc_condition_from_recovered_unit(
        e3a_result["details"] if e3a_result["success"] else [],
        session,
        tenant_schema,
    )

    # Build summary
    name_recovery_by_term: dict[str, int] = {}
    for d in e3a_result["details"]:
        term = d["term"]
        name_recovery_by_term[term] = name_recovery_by_term.get(term, 0) + 1

    # Full condition distribution (simulate what the final state would be)
    # This requires reading ALL analysis_results and replacing E3a/E5 affected rows
    full_condition_dist = _compute_full_condition_distribution(
        session, tenant_schema, e3a_result, e5_result
    )

    summary = {
        "name_recovery_count": e3a_result["updated_count"],
        "name_recovery_by_term": name_recovery_by_term,
        "condition_distribution": full_condition_dist,
    }

    # Print results
    _print_dry_run_results(e3a_result, e5_result, summary)

    return {
        "e3a": e3a_result,
        "e5": e5_result,
        "summary": summary,
    }


def _compute_full_condition_distribution(
    session: Session,
    tenant_schema: str,
    e3a_result: dict,
    e5_result: dict,
) -> dict[str, int]:
    """
    全 analysis_results の condition_canonical 分布を計算する。
    E3a/E5 の変更を仮適用した後の最終分布。
    """
    # Read current distribution
    rows = session.execute(
        text(
            f"""
            SELECT condition_canonical, COUNT(*)
            FROM {tenant_schema}.analysis_results
            GROUP BY condition_canonical
            ORDER BY COUNT(*) DESC
            """
        )
    ).fetchall()
    dist: dict[str, int] = {}
    for canonical, count in rows:
        key = canonical or "(empty)"
        dist[key] = count

    # Apply E5 changes (E3a only changes unit columns, not condition)
    for change in e5_result.get("changes", []):
        old_cond = change["old_condition"] or "(empty)"
        new_cond = change["new_condition"] or "(empty)"
        if old_cond != new_cond:
            dist[old_cond] = dist.get(old_cond, 1) - 1
            if dist[old_cond] <= 0:
                del dist[old_cond]
            dist[new_cond] = dist.get(new_cond, 0) + 1

    return dist


def _print_dry_run_results(
    e3a_result: dict,
    e5_result: dict,
    summary: dict,
) -> None:
    """dry-run 結果を stdout に出力する。"""
    print("=" * 60)
    print("TCG E3a + E5 Unit Recovery — Dry-Run Results")
    print("=" * 60)

    print()
    print("--- E3a: recover_unit_from_product_name ---")
    print(f"  Success: {e3a_result['success']}")
    print(f"  Would recover: {e3a_result['updated_count']} rows")
    if e3a_result.get("aborted"):
        print(f"  ABORTED: {e3a_result['message']}")

    if e3a_result["details"]:
        print()
        print("  NAME_RECOVERY by term:")
        for term, count in sorted(
            summary["name_recovery_by_term"].items(),
            key=lambda x: x[1],
            reverse=True,
        ):
            print(f"    {term}: {count}")

        print()
        print("  Details (first 20):")
        for d in e3a_result["details"][:20]:
            print(
                f"    {d['product_code']:>8} | "
                f"{d['product_name'][:40]:<40} | "
                f"{d['term']} -> {d['canonical']}"
            )

    print()
    print("--- E5: recalc_condition_from_recovered_unit ---")
    print(f"  Success: {e5_result['success']}")
    print(f"  Targets: {e5_result['target_count']}")
    print(f"  Would change: {e5_result['changed_count']}")
    if e5_result.get("aborted"):
        print(f"  ABORTED: {e5_result['message']}")

    if e5_result["changes"]:
        print()
        print("  Changes:")
        for c in e5_result["changes"]:
            print(
                f"    {c['unit_canonical']:>8} | "
                f"{c['old_condition']} -> {c['new_condition']} "
                f"({c['new_basis']})"
            )

    print()
    print("--- Full condition distribution (after E3a+E5) ---")
    for canonical, count in sorted(
        summary["condition_distribution"].items(),
        key=lambda x: x[1],
        reverse=True,
    ):
        print(f"  {canonical}: {count}")

    print()
    print("=" * 60)


__all__ = [
    "unit_recovery_norm",
    "build_unit_recovery_terms",
    "find_term",
    "recover_unit_from_product_name",
    "recalc_condition_from_recovered_unit",
    "run_unit_recovery_dry_run",
    "E3A_MAX_RECOVER",
    "E5_MAX_ROWS",
]
