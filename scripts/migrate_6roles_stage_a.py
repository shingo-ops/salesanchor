#!/usr/bin/env python3
"""
共通6ロール化 段階A — 既存テナントへのロール揃えスクリプト。

【実施内容】
  既存テナントに対してロール名を共通6ロールに揃える。

  対象ロールと判定ロジック（テナントごとに独立して判定）:
    リーダー → マネージャー:
      - 「リーダー」が存在し「マネージャー」が存在しない → UPDATE name（改名）
      - 「マネージャー」が既に存在する → スキップ（改名済みとみなす）
      - どちらも存在しない → 新規追加（seed_system_roles で INSERT）
    仕入れ担当 → 仕入れ:
      - 「仕入れ担当」が存在し「仕入れ」が存在しない → UPDATE name（改名）
      - 「仕入れ」が既に存在する → スキップ
      - どちらも存在しない → 新規追加（seed_system_roles で INSERT）
    発送担当 → 発送:
      - 「発送担当」が存在し「発送」が存在しない → UPDATE name（改名）
      - 「発送」が既に存在する → スキップ
      - どちらも存在しない → 新規追加（seed_system_roles で INSERT）

  オーナー・システム管理者・営業・CS は触らない。
  is_system=true のロールは改名対象外（判定ロジックで除外）。
  改名は権限を変更しない（name のみ UPDATE）。
  新規追加のみ初期権限を入れる（seed_system_roles の既存挙動を流用）。

【冪等性】
  複数回実行しても安全:
    - 改名済み（マネージャー等が既に存在）→ スキップ
    - seed_system_roles の ON CONFLICT (tenant_id, name) DO UPDATE で重複作成なし
    - 改名時に「リーダー」「仕入れ担当」「発送担当」が残っていない → 何もしない

【安全ブレーキ】
  --tenant-id は必須（未指定で終了）。
  対象に tenant_id=4（本番）が含まれる場合は --yes-production フラグが必要。

実行方法（VPS、backend コンテナ内）:
  # tenant_006 のみ（通常）:
  docker compose exec backend python /app/scripts/migrate_6roles_stage_a.py --tenant-id 6

  # 本番 tenant_004 を含む場合（Shingo GO 後のみ）:
  docker compose exec backend python /app/scripts/migrate_6roles_stage_a.py --tenant-id 4 --yes-production

変更履歴:
  2026-06-26: 初版作成（共通6ロール化 段階A）
  2026-06-26: --tenant-id 必須化・本番ガード追加・件数ログ追加
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

_APP_ROOT = Path(__file__).resolve().parent.parent
if str(_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.services.tenant import seed_system_roles

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logger.error("DATABASE_URL 環境変数が設定されていません")
    sys.exit(1)

# 本番テナントID（このIDを含む場合 --yes-production が必須）
_PRODUCTION_TENANT_IDS = {4}

# 改名マッピング: {旧名: 新名}
# is_system=false のロールのみ対象（is_system チェックを SQL で行う）
_RENAME_MAP = {
    "リーダー": "マネージャー",
    "仕入れ担当": "仕入れ",
    "発送担当": "発送",
}


async def _count_roles(conn, schema: str, tenant_id: int) -> tuple[int, int]:
    """roles 件数と user_roles 件数を返す。"""
    roles_count = (await conn.execute(
        text(f"SELECT COUNT(*) FROM {schema}.roles WHERE tenant_id = :tid"),
        {"tid": tenant_id},
    )).scalar_one()
    user_roles_count = (await conn.execute(
        text(f"SELECT COUNT(*) FROM {schema}.user_roles"),
    )).scalar_one()
    return int(roles_count), int(user_roles_count)


async def _migrate_tenant(engine, tenant_id: int) -> dict:
    """単一テナントに対してロール揃えを実施。結果サマリを返す。"""
    schema = f"tenant_{tenant_id:03d}"
    renamed: list[str] = []
    skipped: list[str] = []
    added: list[str] = []

    async with engine.begin() as conn:
        await conn.execute(text(f"SET search_path = {schema}, public"))
        await conn.execute(text(f"SET app.tenant_id = '{tenant_id}'"))

        # --- 件数ログ（前） ---
        roles_before, user_roles_before = await _count_roles(conn, schema, tenant_id)
        logger.info(
            "  [before] roles=%d / user_roles=%d",
            roles_before, user_roles_before,
        )

        # --- ① 「在れば改名／無ければ追加」の判定 ---
        for old_name, new_name in _RENAME_MAP.items():
            # 新名が既に存在するか確認
            row_new = (await conn.execute(
                text(f"SELECT id FROM {schema}.roles WHERE tenant_id = :tid AND name = :name"),
                {"tid": tenant_id, "name": new_name},
            )).first()

            if row_new is not None:
                # 新名が既に存在 → 改名済み or 既追加済み → スキップ
                skipped.append(f"{old_name}→{new_name}（{new_name} 既存）")
                continue

            # 旧名が存在するか確認（is_system=false のみ対象）
            row_old = (await conn.execute(
                text(f"""
                    SELECT id FROM {schema}.roles
                    WHERE tenant_id = :tid AND name = :name AND is_system = false
                """),
                {"tid": tenant_id, "name": old_name},
            )).first()

            if row_old is not None:
                # 旧名が存在 → 改名（name のみ UPDATE、権限は触らない）
                await conn.execute(
                    text(f"""
                        UPDATE {schema}.roles
                        SET name = :new_name, updated_at = NOW()
                        WHERE id = :id
                    """),
                    {"new_name": new_name, "id": row_old.id},
                )
                logger.info("  %s: %s → %s（改名）", schema, old_name, new_name)
                renamed.append(f"{old_name}→{new_name}")
            else:
                # 旧名も新名も存在しない → 新規追加（seed_system_roles で INSERT）
                # seed_system_roles は DEFAULT_ROLES を全件ループするが、
                # 既存ロールは ON CONFLICT で更新のみ（権限は新規のみ付与）なので安全。
                logger.info("  %s: %s なし → seed で新規追加", schema, new_name)
                added.append(new_name)

        # --- ② seed_system_roles で新規追加ロールの INSERT + 既存ロールの color/priority/description 同期 ---
        # 改名後のロール（マネージャー/仕入れ/発送）が DB に存在する状態で seed を呼ぶため、
        # ON CONFLICT が発動して追加分は created_row のみ処理される。
        await seed_system_roles(conn, tenant_id, schema)

        # --- 件数ログ（後） ---
        roles_after, user_roles_after = await _count_roles(conn, schema, tenant_id)
        logger.info(
            "  [after]  roles=%d (+%d) / user_roles=%d (変化=%+d)",
            roles_after, roles_after - roles_before,
            user_roles_after, user_roles_after - user_roles_before,
        )

    return {"renamed": renamed, "skipped": skipped, "added": added}


async def main(tenant_ids: list[int], yes_production: bool) -> None:
    # --- 本番ガード ---
    production_targets = _PRODUCTION_TENANT_IDS & set(tenant_ids)
    if production_targets and not yes_production:
        logger.error(
            "対象に本番テナント %s が含まれています。"
            " 本番適用には --yes-production フラグが必要です。中断します。",
            sorted(production_targets),
        )
        sys.exit(1)

    if yes_production and production_targets:
        logger.warning(
            "⚠ 本番テナント %s を対象に実行します（--yes-production 指定）。",
            sorted(production_targets),
        )

    url = DATABASE_URL
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]

    engine = create_async_engine(url, echo=False)
    try:
        logger.info("=== 共通6ロール化 段階A 開始 ===")
        logger.info("対象テナントID: %s", tenant_ids)

        total_renamed = 0
        total_added = 0
        for tenant_id in tenant_ids:
            logger.info("--- tenant_id=%d ---", tenant_id)
            result = await _migrate_tenant(engine, tenant_id)
            for r in result["renamed"]:
                logger.info("  ✓ 改名: %s", r)
            for s in result["skipped"]:
                logger.info("  - スキップ: %s", s)
            for a in result["added"]:
                logger.info("  ✓ 新規追加: %s", a)
            total_renamed += len(result["renamed"])
            total_added += len(result["added"])

        logger.info("=== 完了 === 改名 %d 件 / 新規追加 %d 件", total_renamed, total_added)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="共通6ロール化 段階A — 既存テナントのロール名を揃える",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
  # tenant_006 のみ（通常）:
  python migrate_6roles_stage_a.py --tenant-id 6

  # 本番 tenant_004 を含む場合（Shingo GO 後のみ）:
  python migrate_6roles_stage_a.py --tenant-id 4 --yes-production
        """,
    )
    parser.add_argument(
        "--tenant-id",
        type=int,
        nargs="+",
        dest="tenant_ids",
        required=True,  # 必須（未指定で終了）
        metavar="ID",
        help="対象テナントID（必須・複数指定可）。例: --tenant-id 6",
    )
    parser.add_argument(
        "--yes-production",
        action="store_true",
        dest="yes_production",
        help="本番テナント（tenant_id=4）を含む場合に必要な明示フラグ",
    )
    args = parser.parse_args()
    asyncio.run(main(args.tenant_ids, args.yes_production))
