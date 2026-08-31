"""
MIG-04 Phase 4: 並行運用比較レポートサービス。

同一 extraction_items に対して:
  - compat-v1 (GAS 時代の照合結果, DB 既存値)
  - name-first-v1 (サーバー新エンジン, インメモリ計算)
を並べた仕入元別比較レポートを生成する。

DB への書き込みは一切行わない（compat-v1 を上書きしない）。

TCG解析システムは tenant_004 専用スキーマ。全 SQL は tenant_004. で修飾する。
"""
from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.tcg_analyzer_svc import (
    match_pid_name_first,
    resolve_unit,
)

logger = logging.getLogger(__name__)

# TCG解析システムは tenant_004 専用スキーマ
TCG_SCHEMA = "tenant_004"


# ---------------------------------------------------------------------------
# ルックアップマップのロード（非同期版）
# ---------------------------------------------------------------------------


async def _load_lookup_maps_async(db: AsyncSession) -> tuple[dict, dict, dict, dict, dict]:
    """照合に必要なマスタをロードする（AsyncSession 版）。"""
    # 商品コード → UUID
    rows = (
        await db.execute(text(f"SELECT code, id FROM {TCG_SCHEMA}.tcg_products WHERE is_active = TRUE"))
    ).fetchall()
    product_code_to_uuid: dict[str, str] = {r[0]: str(r[1]) for r in rows}

    # 単位エイリアス
    rows = (
        await db.execute(
            text(
                f"""
                SELECT ua.alias_text, u.canonical, u.id
                FROM {TCG_SCHEMA}.unit_aliases ua
                JOIN {TCG_SCHEMA}.units u ON u.id = ua.unit_id
                WHERE u.is_active = TRUE
                """
            )
        )
    ).fetchall()
    unit_alias_to_canonical: dict[str, str] = {r[0]: r[1] for r in rows}
    unit_canonical_to_uuid: dict[str, str] = {r[1]: str(r[2]) for r in rows}

    # 状態エイリアス
    rows = (
        await db.execute(
            text(
                f"""
                SELECT ca.alias_text, c.canonical, c.id
                FROM {TCG_SCHEMA}.condition_aliases ca
                JOIN {TCG_SCHEMA}.conditions c ON c.id = ca.condition_id
                WHERE c.is_active = TRUE
                """
            )
        )
    ).fetchall()
    cond_alias_to_canonical: dict[str, str] = {r[0]: r[1] for r in rows}
    cond_canonical_to_uuid: dict[str, str] = {r[1]: str(r[2]) for r in rows}

    return (
        product_code_to_uuid,
        unit_alias_to_canonical,
        unit_canonical_to_uuid,
        cond_alias_to_canonical,
        cond_canonical_to_uuid,
    )


async def _load_product_keywords_async(db: AsyncSession) -> tuple[dict, dict]:
    """商品キーワードをロードする（AsyncSession 版）。"""
    # 検索キーワード
    rows = (
        await db.execute(
            text(
                f"""
                SELECT p.code, psk.keyword
                FROM {TCG_SCHEMA}.product_search_keywords psk
                JOIN {TCG_SCHEMA}.tcg_products p ON p.id = psk.product_id
                WHERE p.is_active = TRUE
                ORDER BY p.code, psk.position
                """
            )
        )
    ).fetchall()
    search_kw: dict[str, list[str]] = {}
    for code, kw in rows:
        search_kw.setdefault(code, []).append(kw)

    # 除外キーワード
    rows = (
        await db.execute(
            text(
                f"""
                SELECT p.code, pek.keyword
                FROM {TCG_SCHEMA}.product_exclude_keywords pek
                JOIN {TCG_SCHEMA}.tcg_products p ON p.id = pek.product_id
                WHERE p.is_active = TRUE
                ORDER BY p.code, pek.position
                """
            )
        )
    ).fetchall()
    exclude_kw: dict[str, list[str]] = {}
    for code, kw in rows:
        exclude_kw.setdefault(code, []).append(kw)

    return search_kw, exclude_kw


# ---------------------------------------------------------------------------
# 比較レポート生成
# ---------------------------------------------------------------------------


async def build_parallel_report(db: AsyncSession) -> dict:
    """
    仕入元別の並行比較レポートを生成する。

    Returns:
      {
        "summary": {
          "total_items": int,
          "compat_v1_pid_resolved": int,
          "name_first_v1_pid_resolved": int,
          "compat_v1_pid_pct": float,
          "name_first_v1_pid_pct": float,
        },
        "suppliers": [
          {
            "sp_code": str,
            "supplier_name": str,
            "total": int,
            "compat_v1": {"pid_resolved": int, "pid_pct": float, "unit_resolved": int},
            "name_first_v1": {"pid_resolved": int, "pid_pct": float, "unit_resolved": int},
            "pid_pct_diff": float,  # name_first_v1 - compat_v1
          },
          ...
        ]
      }
    """
    logger.info("[parallel_report] building report...")

    # ルックアップマップのロード
    (
        product_code_to_uuid,
        unit_alias_to_canonical,
        _,
        cond_alias_to_canonical,
        _,
    ) = await _load_lookup_maps_async(db)
    search_kw, exclude_kw = await _load_product_keywords_async(db)
    product_codes = list(product_code_to_uuid.keys())

    # extraction_items + compat-v1 analysis_results + supplier info を一括取得
    rows = (
        await db.execute(
            text(
                f"""
                SELECT
                    ts.code AS sp_code,
                    ts.name AS supplier_name,
                    ei.id AS item_id,
                    ei.raw_product_name,
                    ei.raw_unit,
                    ar.pid_resolved AS compat_pid_resolved,
                    ar.unit_resolved AS compat_unit_resolved
                FROM {TCG_SCHEMA}.extraction_items ei
                JOIN {TCG_SCHEMA}.extraction_jobs ej ON ei.extraction_job_id = ej.id
                JOIN {TCG_SCHEMA}.source_messages sm ON ej.source_message_id = sm.id
                JOIN {TCG_SCHEMA}.supplier_channels sc ON sm.supplier_channel_id = sc.id
                JOIN {TCG_SCHEMA}.tcg_suppliers ts ON sc.supplier_id = ts.id
                LEFT JOIN {TCG_SCHEMA}.analysis_results ar
                    ON ar.extraction_item_id = ei.id
                    AND ar.engine_version = 'compat-v1'
                WHERE sm.is_active = TRUE
                ORDER BY ts.code, ei.id
                """
            )
        )
    ).fetchall()

    logger.info("[parallel_report] loaded %d items", len(rows))

    # 仕入元別に集計
    supplier_map: dict[str, dict] = {}

    for row in rows:
        sp_code = row[0]
        supplier_name = row[1]
        raw_product_name = row[3] or ""
        raw_unit = row[4] or ""
        compat_pid_resolved = row[5]
        compat_unit_resolved = row[6]

        if sp_code not in supplier_map:
            supplier_map[sp_code] = {
                "sp_code": sp_code,
                "supplier_name": supplier_name,
                "total": 0,
                "compat_v1_pid": 0,
                "compat_v1_unit": 0,
                "compat_v1_has_result": 0,
                "name_first_v1_pid": 0,
                "name_first_v1_unit": 0,
            }

        s = supplier_map[sp_code]
        s["total"] += 1

        # compat-v1 集計
        if compat_pid_resolved is not None:
            s["compat_v1_has_result"] += 1
            if compat_pid_resolved:
                s["compat_v1_pid"] += 1
            if compat_unit_resolved:
                s["compat_v1_unit"] += 1

        # name-first-v1 インメモリ計算
        _, _, pid_resolved, _ = match_pid_name_first(
            raw_product_name, product_codes, search_kw, exclude_kw
        )
        _, unit_resolved = resolve_unit(raw_unit, unit_alias_to_canonical)

        if pid_resolved:
            s["name_first_v1_pid"] += 1
        if unit_resolved:
            s["name_first_v1_unit"] += 1

    # 出力形式に変換
    suppliers = []
    total_items = 0
    total_compat_pid = 0
    total_nf_pid = 0

    for sp_code in sorted(supplier_map.keys()):
        s = supplier_map[sp_code]
        total = s["total"]
        c_pid = s["compat_v1_pid"]
        nf_pid = s["name_first_v1_pid"]
        c_unit = s["compat_v1_unit"]
        nf_unit = s["name_first_v1_unit"]

        c_pid_pct = round(100.0 * c_pid / total, 1) if total > 0 else 0.0
        nf_pid_pct = round(100.0 * nf_pid / total, 1) if total > 0 else 0.0

        suppliers.append(
            {
                "sp_code": sp_code,
                "supplier_name": s["supplier_name"],
                "total": total,
                "compat_v1": {
                    "pid_resolved": c_pid,
                    "pid_pct": c_pid_pct,
                    "unit_resolved": c_unit,
                    "has_result": s["compat_v1_has_result"],
                },
                "name_first_v1": {
                    "pid_resolved": nf_pid,
                    "pid_pct": nf_pid_pct,
                    "unit_resolved": nf_unit,
                },
                "pid_pct_diff": round(nf_pid_pct - c_pid_pct, 1),
            }
        )

        total_items += total
        total_compat_pid += c_pid
        total_nf_pid += nf_pid

    summary = {
        "total_items": total_items,
        "compat_v1_pid_resolved": total_compat_pid,
        "name_first_v1_pid_resolved": total_nf_pid,
        "compat_v1_pid_pct": round(100.0 * total_compat_pid / total_items, 1) if total_items else 0.0,
        "name_first_v1_pid_pct": round(100.0 * total_nf_pid / total_items, 1) if total_items else 0.0,
        "supplier_count": len(suppliers),
    }

    logger.info(
        "[parallel_report] done. total=%d compat_v1_pid_pct=%.1f%% name_first_v1_pid_pct=%.1f%%",
        total_items,
        summary["compat_v1_pid_pct"],
        summary["name_first_v1_pid_pct"],
    )

    return {"summary": summary, "suppliers": suppliers}
