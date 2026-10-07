"""実関数 load_user_permissions を PostgreSQL で流す試験（owner / admin は権限マスタから計算する）。

ゲートは CI が実際に設定する RLS_ADMIN_DATABASE_URL（test_rls_bootstrap_ordering.py と同じ形）。
conftest.py の自動モック bypass_permissions は、この試験だけ同名のフィクスチャで上書きして無効にする。
実関数は import 時に束縛しておく（自動モックは module 属性を差し替えるため）。

準備の順序（検証する）: 共有 public 表 → 実際の 070 と 20260604_050000（public.tenant_settings の構造）→ 試験用の権限キー →
その後で試験用テナントを作る。070 には「全テナントに phase 'A' の行を入れる」値の書き込み（070:75-77）があるので、
試験用テナントの行が public.tenants に入る前に流し、tenant_settings に試験用テナントの行が無いことを
create_tenant_schema の前に確かめる（順序を仮定せず、検証する）。070 の phase.switch の INSERT は ON CONFLICT DO NOTHING。
試験が入れた行（権限キー・テナント・tenant_settings）だけを、後始末で消す。使い捨ての CI 用 DB への操作。
"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.auth.dependencies import load_user_permissions as real_load_user_permissions
from app.auth.system_roles import ROLE_KEY_ADMIN, ROLE_KEY_OWNER, SYSTEM_MANAGE_KEY
from tests.rls_bootstrap import (
    _apply_migration_on_conn,
    _bootstrap_public_shared,
    _ensure_public_users,
    bootstrap_tenant_schema,
    public_bootstrap_lock,
    tenant_rls_session,
    tenant_schema_lock,
)

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")

_TENANT_ID = 998
_SCHEMA = f"tenant_{_TENANT_ID:03d}"
_NEW_KEY = "zz.new_key.test"
# この試験が検証する権限キー。bootstrap の DB に無ければ、試験の準備で自分で入れる（試験のデータは試験が持つ）
_OWN_KEYS = (
    ("goals.view", "goals", "view", "目標を閲覧する", "目標管理"),
    ("goals.edit", "goals", "edit", "目標を作成・編集する", "目標管理"),
    (_NEW_KEY, "zz", "new_key", "test key", "test"),
)
_USERS = {"owner": 9801, "admin": 9802, "cs": 9803, "admin_plus": 9804, "owner_cs": 9805}


@pytest.fixture(autouse=True)
def bypass_permissions():
    """conftest.py の同名フィクスチャを上書きし、この試験では実関数を使う。"""
    yield


async def _remove_test_tenant_rows(conn) -> None:
    """この試験のテナント（id 998）が入れた行だけを消す。他のテナントの行には触れない。"""
    await conn.execute(text(f"DROP SCHEMA IF EXISTS {_SCHEMA} CASCADE"))
    exists = await conn.scalar(text("SELECT to_regclass('public.tenant_settings')"))
    if exists is not None:
        await conn.execute(text("DELETE FROM public.tenant_settings WHERE tenant_id = :t"), {"t": _TENANT_ID})
    exists = await conn.scalar(text("SELECT to_regclass('public.tenants')"))
    if exists is not None:
        await conn.execute(text("DELETE FROM public.tenants WHERE id = :t"), {"t": _TENANT_ID})


async def _role_id(session, name: str) -> int:
    row = await session.execute(text("SELECT id FROM roles WHERE name = :n"), {"n": name})
    return row.scalar_one()


async def _assign(session, user_id: int, role_id: int) -> None:
    await session.execute(
        text("INSERT INTO user_roles (user_id, role_id) VALUES (:u, :r)"),
        {"u": user_id, "r": role_id},
    )


async def _call(session, user_id: int) -> set[str]:
    with patch("app.auth.dependencies.get_cached_user_permissions", AsyncMock(return_value=None)), patch(
        "app.auth.dependencies.cache_user_permissions", AsyncMock()
    ):
        return await real_load_user_permissions(session, _TENANT_ID, user_id)


@pytest.mark.skipif(
    not ADMIN_PG_URL,
    reason="実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / TEST_PG_URL 未設定)。",
)
@pytest.mark.asyncio
async def test_real_load_user_permissions_computes_owner_and_admin_and_fresh_tenant_state():
    admin_engine = create_async_engine(ADMIN_PG_URL, echo=False)
    session_factory = sessionmaker(admin_engine, class_=AsyncSession, expire_on_commit=False)
    inserted_keys: list[str] = []
    try:
        async with tenant_schema_lock(admin_engine, _TENANT_ID):
            # 1) 前回の残りがあれば消す（この試験のテナントの行だけ）
            async with admin_engine.begin() as conn:
                await _remove_test_tenant_rows(conn)
            # 2) 共有 public 表（public.tenants / public.permissions）を用意する。試験用テナントの行はまだ入れない
            async with public_bootstrap_lock(admin_engine):
                async with admin_engine.begin() as conn:
                    await _bootstrap_public_shared(conn)
                    await _ensure_public_users(conn)
                    # 3) 実際の 070 と 20260604_050000（public.tenant_settings の構造。本番 DDL をテストにコピーしない）
                    await _apply_migration_on_conn(conn, "070_add_spreadsheet_phase.sql")
                    await _apply_migration_on_conn(conn, "20260604_050000_add_tenant_policy_columns.sql")
                    # 4) 試験が使う権限キー（作成時の付与は、権限マスタにあるキーだけが対象）
                    for key, resource, action, description, category in _OWN_KEYS:
                        inserted = await conn.execute(
                            text(
                                "INSERT INTO public.permissions (key, resource, action, description, category) "
                                "VALUES (:k, :r, :a, :d, :c) ON CONFLICT (key) DO NOTHING RETURNING key"
                            ),
                            {"k": key, "r": resource, "a": action, "d": description, "c": category},
                        )
                        if inserted.first() is not None:
                            inserted_keys.append(key)
            # 5) 順序の検証: 070 の「全テナントに phase 'A' を入れる」書き込みが、試験用テナントに触れていない
            async with admin_engine.connect() as conn:
                leftover = await conn.execute(
                    text("SELECT count(*) FROM public.tenant_settings WHERE tenant_id = :t"), {"t": _TENANT_ID}
                )
                assert leftover.scalar_one() == 0
            # 6) 試験用テナントを作る（create_tenant_schema が tenant_settings に phase 'B' の行を入れる）
            await bootstrap_tenant_schema(admin_engine, _TENANT_ID)

            async with admin_engine.begin() as conn:
                all_keys = {r[0] for r in (await conn.execute(text("SELECT key FROM public.permissions"))).all()}
            assert SYSTEM_MANAGE_KEY in all_keys and _NEW_KEY in all_keys

            async with tenant_rls_session(session_factory, _TENANT_ID) as session:
                owner_id = await _role_id(session, "オーナー")
                admin_id = await _role_id(session, "システム管理者")
                cs_id = await _role_id(session, "CS")
                await _assign(session, _USERS["owner"], owner_id)
                await _assign(session, _USERS["admin"], admin_id)
                await _assign(session, _USERS["cs"], cs_id)
                await _assign(session, _USERS["admin_plus"], admin_id)
                await _assign(session, _USERS["owner_cs"], owner_id)
                await _assign(session, _USERS["owner_cs"], cs_id)
                # 5b: admin に加え、system.manage を明示的に付与した別ロールを持つユーザー
                extra = await session.execute(
                    text(
                        "INSERT INTO roles (tenant_id, name, priority, is_system) "
                        "VALUES (:t, 'extra-sysmanage', 10, FALSE) RETURNING id"
                    ),
                    {"t": _TENANT_ID},
                )
                extra_id = extra.scalar_one()
                await session.execute(
                    text(
                        "INSERT INTO role_permissions (role_id, permission_id) "
                        "SELECT :r, id FROM public.permissions WHERE key = :k"
                    ),
                    {"r": extra_id, "k": SYSTEM_MANAGE_KEY},
                )
                await _assign(session, _USERS["admin_plus"], extra_id)

                # 新しい鍵は role_permissions の行が無い状態で owner / admin に届く
                new_key_rows = await session.execute(
                    text(
                        "SELECT count(*) FROM role_permissions rp JOIN public.permissions p ON p.id = rp.permission_id "
                        "WHERE p.key = :k"
                    ),
                    {"k": _NEW_KEY},
                )
                assert new_key_rows.scalar_one() == 0

                owner_keys = await _call(session, _USERS["owner"])
                admin_keys = await _call(session, _USERS["admin"])
                cs_keys = await _call(session, _USERS["cs"])
                admin_plus_keys = await _call(session, _USERS["admin_plus"])
                owner_cs_keys = await _call(session, _USERS["owner_cs"])

                assert owner_keys == all_keys
                assert admin_keys == all_keys - {SYSTEM_MANAGE_KEY}
                assert _NEW_KEY in owner_keys and _NEW_KEY in admin_keys and _NEW_KEY not in cs_keys
                stored_cs = {
                    r[0]
                    for r in (
                        await session.execute(
                            text(
                                "SELECT p.key FROM role_permissions rp JOIN public.permissions p ON p.id = rp.permission_id "
                                "WHERE rp.role_id = :r"
                            ),
                            {"r": cs_id},
                        )
                    ).all()
                }
                assert cs_keys == stored_cs
                assert SYSTEM_MANAGE_KEY in admin_plus_keys  # 5b: 和集合
                assert admin_plus_keys == all_keys
                assert owner_cs_keys == all_keys

                # 新テナントの状態: system_key / is_system / goals 付与 / phase 'B'
                roles = {
                    r[0]: (r[1], r[2])
                    for r in (await session.execute(text("SELECT name, system_key, is_system FROM roles"))).all()
                }
                assert roles["オーナー"] == (ROLE_KEY_OWNER, True)
                assert roles["システム管理者"] == (ROLE_KEY_ADMIN, True)
                assert all(roles[n][0] is None for n in ("マネージャー", "営業", "CS", "仕入れ", "発送"))
                goals = {
                    (r[0], r[1])
                    for r in (
                        await session.execute(
                            text(
                                "SELECT r.name, p.key FROM role_permissions rp "
                                "JOIN roles r ON r.id = rp.role_id JOIN public.permissions p ON p.id = rp.permission_id "
                                "WHERE p.key IN ('goals.view', 'goals.edit')"
                            )
                        )
                    ).all()
                }
                for name in ("マネージャー", "営業", "CS", "仕入れ", "発送"):
                    assert (name, "goals.view") in goals
                assert ("マネージャー", "goals.edit") in goals

            async with admin_engine.connect() as conn:
                phase = await conn.execute(
                    text("SELECT spreadsheet_phase FROM public.tenant_settings WHERE tenant_id = :t"),
                    {"t": _TENANT_ID},
                )
                assert phase.scalar_one() == "B"
    finally:
        async with admin_engine.begin() as conn:
            await _remove_test_tenant_rows(conn)
            for key in inserted_keys:  # この試験が入れたキーだけを消す（元からあるキーは消さない）
                await conn.execute(text("DELETE FROM public.permissions WHERE key = :k"), {"k": key})
        await admin_engine.dispose()
