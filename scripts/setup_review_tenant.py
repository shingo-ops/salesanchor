#!/usr/bin/env python3
"""Meta App Review 撮影用テナント (tenant-review) セットアップスクリプト。

ADR-028: Meta App Review 撮影用テナント分離の実装。

実行方法（VPS側、backendコンテナ内）:
  # 通常実行（パスワードは変更しない）
  docker compose exec -e ALLOW_REVIEW_TENANT_SETUP=1 backend \\
      python /app/scripts/setup_review_tenant.py

  # パスワードリセット（明示フラグ必須）
  docker compose exec \\
      -e ALLOW_REVIEW_TENANT_SETUP=1 \\
      -e ALLOW_REVIEW_TENANT_PASSWORD_RESET=1 \\
      backend python /app/scripts/setup_review_tenant.py

前提:
  - DATABASE_URL 環境変数が設定されていること
  - ALLOW_REVIEW_TENANT_SETUP=1 を環境変数で渡すこと（誤実行防止のガード）

冪等性:
  - 複数回実行しても安全。既存テナント・ユーザーを重複作成しない。
  - 既存ユーザーにパスワードがある場合、パスワードは変更しない（デフォルト）。

注意:
  - review@salesanchor.jp が既存テナントに紐付いている場合、新テナントに付け替えます。
    既存テナント（tenant_004 等）のスキーマデータは一切変更しません（AC-3）。
  - Meta OAuth 再接続は OAuth フロー経由で別途実施してください（自動化不可）。
  - パスワードリセット時のみ /tmp/review_tenant_setup_*.txt に出力します。
    コンテナ再起動で /tmp は消えるため、Shingo に安全な手段で共有すること。
    ChatGPT / PR 本文 / GitHub コメントにパスワードを書かないこと。

変更履歴:
  2026-05-14: ADR-028 初版作成
  2026-06-14: ADR-089 対応（customers 廃止 → _seed_demo_customers 削除）
              ADR-138 対応（password_hash 廃止）
              パスワード保護: 既存ユーザーへの無条件 password reset を禁止、
              ALLOW_REVIEW_TENANT_PASSWORD_RESET=1 で明示許可した場合のみ変更可
  2026-11-05: ADR-1013 便6 対応（自社ログインのパスワード password_argon2_hash を書く）
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

_APP_ROOT = Path(__file__).resolve().parent.parent
if str(_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

TENANT_CODE = "tenant-review"
TENANT_NAME = "Sales Anchor App Review"
REVIEW_EMAIL = "review@salesanchor.jp"
REVIEW_DISPLAY_NAME = "App Review"


# ---------------------------------------------------------------------------
# ガードチェック
# ---------------------------------------------------------------------------

def _check_guard() -> None:
    if os.getenv("ALLOW_REVIEW_TENANT_SETUP") != "1":
        logger.error(
            "誤実行防止: 環境変数 ALLOW_REVIEW_TENANT_SETUP=1 を付けて実行してください。\n"
            "  例: docker compose exec -e ALLOW_REVIEW_TENANT_SETUP=1 backend"
            " python /app/scripts/setup_review_tenant.py"
        )
        sys.exit(1)


def _password_reset_requested() -> bool:
    """ALLOW_REVIEW_TENANT_PASSWORD_RESET=1 が明示されているか。"""
    return os.getenv("ALLOW_REVIEW_TENANT_PASSWORD_RESET") == "1"


# ---------------------------------------------------------------------------
# パスワード
# ---------------------------------------------------------------------------

def _should_write_password(has_password: bool, reset: bool) -> bool:
    """パスワードを書くか。リセット指定のときと、まだパスワードが無いときだけ書く。"""
    return reset or not has_password


async def _has_password(engine) -> bool:
    """review 用の利用者がいて、自社ログインのパスワードを持っているか。"""
    async with engine.begin() as conn:
        # ADR-1018 段階③便C: public.users の読み書きは運営文脈で行う
        await conn.execute(text("SET app.is_operator = 'true'"))
        row = (await conn.execute(
            text("SELECT password_argon2_hash FROM public.users WHERE email = :email"),
            {"email": REVIEW_EMAIL},
        )).first()
    return row is not None and row[0] is not None


# ---------------------------------------------------------------------------
# DB: テナント
# ---------------------------------------------------------------------------

async def _ensure_tenant(engine) -> int:
    """tenant-review テナントを作成または取得し、ID を返す（冪等）。"""
    async with engine.begin() as conn:
        row = (await conn.execute(
            text("SELECT id FROM public.tenants WHERE tenant_code = :code"),
            {"code": TENANT_CODE},
        )).first()
        if row:
            logger.info("テナント '%s' 既存 (id=%d)", TENANT_CODE, row[0])
            return int(row[0])

        # ADR-1018 段階③便B: public.tenants への書込は運営文脈のときだけ通る
        await conn.execute(text("SET app.is_operator = 'true'"))
        row = (await conn.execute(
            text("""
                INSERT INTO public.tenants (tenant_name, tenant_code, is_active)
                VALUES (:name, :code, TRUE)
                RETURNING id
            """),
            {"name": TENANT_NAME, "code": TENANT_CODE},
        )).first()
        tenant_id = int(row[0])
        logger.info("テナント '%s' 新規作成 (id=%d)", TENANT_CODE, tenant_id)

        schema_name = f"tenant_{tenant_id:03d}"
        await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
        logger.info("  スキーマ %s 作成", schema_name)

    return tenant_id


async def _apply_tenant_schema(engine, tenant_id: int) -> None:
    """テナントスキーマにテーブル・RLS・システムロールを適用する（冪等）。"""
    from app.services.tenant import (
        _TENANT_TABLES_SQL,
        _RLS_ENABLE_SQL,
        _RLS_POLICY_SQL,
        seed_system_roles,
        _split_sql_preserving_do_blocks,
    )

    schema_name = f"tenant_{tenant_id:03d}"
    logger.info("スキーマ %s にテーブル・RLS・ロールを適用中...", schema_name)

    async with engine.begin() as conn:
        tables_sql = _TENANT_TABLES_SQL.format(
            schema=schema_name, schema_raw=schema_name, tenant_id=tenant_id
        )
        for stmt in _split_sql_preserving_do_blocks(tables_sql):
            stmt = stmt.strip()
            if stmt:
                await conn.execute(text(stmt))

        enable_sql = _RLS_ENABLE_SQL.format(schema=schema_name)
        for stmt in enable_sql.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                await conn.execute(text(stmt))

        policy_sql = _RLS_POLICY_SQL.format(schema=schema_name, schema_raw=schema_name)
        await conn.execute(text(policy_sql))

        await seed_system_roles(conn, tenant_id, schema_name)

    logger.info("  テーブル + RLS + ロールシード完了")


# ---------------------------------------------------------------------------
# DB: ユーザー
# ---------------------------------------------------------------------------

async def _resolve_role_id(conn, tenant_id: int, schema_name: str, role_name: str) -> int:
    await conn.execute(text(f"SET search_path = {schema_name}, public"))
    await conn.execute(text(f"SET app.tenant_id = '{tenant_id}'"))
    row = (await conn.execute(
        text("SELECT id FROM roles WHERE tenant_id = :tid AND name = :name"),
        {"tid": tenant_id, "name": role_name},
    )).first()
    if not row:
        raise RuntimeError(
            f"テナント {tenant_id} に CRM ロール '{role_name}' が存在しません。"
            " seed_system_roles が完了しているか確認してください。"
        )
    return int(row[0])


async def _create_staff_record(
    conn,
    *,
    tenant_id: int,
    user_id: int,
    email: str,
    display_name: str,
    role_id: int,
) -> int:
    """per-tenant staff レコードを作成する（冪等: 既存なら skip）。"""
    existing = (await conn.execute(
        text("SELECT id FROM staff WHERE primary_email = :email"),
        {"email": email},
    )).first()
    if existing:
        staff_id = int(existing[0])
        logger.info("  staff は既存 (id=%d) のため作成 skip", staff_id)
        await conn.execute(
            text("INSERT INTO staff_ui_preferences (staff_id) VALUES (:sid) ON CONFLICT DO NOTHING"),
            {"sid": staff_id},
        )
        return staff_id

    parts = display_name.replace("　", " ").split(" ", 1)
    surname_jp = parts[0][:50] if parts else "Review"
    given_name_jp = parts[1][:50] if len(parts) >= 2 else "User"

    row = (await conn.execute(
        text("""
            INSERT INTO staff (
                tenant_id, user_id, staff_code,
                surname_jp, given_name_jp,
                primary_email, role_id, status
            )
            VALUES (
                :tid, :uid, :code,
                :sjp, :gjp,
                :email, :rid, 'active'
            )
            RETURNING id
        """),
        {
            "tid": tenant_id,
            "uid": user_id,
            "code": f"EMP-R-{uuid.uuid4().hex[:12]}",
            "sjp": surname_jp,
            "gjp": given_name_jp,
            "email": email,
            "rid": role_id,
        },
    )).first()
    staff_id = int(row[0])
    await conn.execute(
        text("UPDATE staff SET staff_code = :code WHERE id = :id"),
        {"code": f"EMP-{staff_id:05d}", "id": staff_id},
    )
    await conn.execute(
        text("INSERT INTO staff_ui_preferences (staff_id) VALUES (:sid) ON CONFLICT DO NOTHING"),
        {"sid": staff_id},
    )
    logger.info("  staff 作成 (id=%d, user_id=%d)", staff_id, user_id)
    return staff_id


async def _setup_user(engine, tenant_id: int, password_hash: str | None) -> int:
    """public.users にユーザーを登録・付け替え、staff レコードを作成する。

    AC-3 適合: public.users.tenant_id の UPDATE は公開スキーマへの変更であり、
    既存業務テナント（tenant_004 等）のスキーマデータには一切手を加えない。
    既存テナントの staff レコードはそのまま保持する。

    password_hash を渡したときだけ、自社ログインのパスワード（password_argon2_hash）を書き、古いセッションを切る。
    """
    schema_name = f"tenant_{tenant_id:03d}"

    async with engine.begin() as conn:
        # ADR-1018 段階③便C: public.users への書込は運営文脈のときだけ通る
        await conn.execute(text("SET app.is_operator = 'true'"))
        existing = (await conn.execute(
            text("SELECT id, tenant_id FROM public.users WHERE email = :email"),
            {"email": REVIEW_EMAIL},
        )).first()

        if existing:
            user_id, current_tenant_id = int(existing[0]), int(existing[1])
            if current_tenant_id != tenant_id:
                # AC-3: public.users.tenant_id の付け替えのみ。既存テナントスキーマは不変。
                await conn.execute(
                    text("""
                        UPDATE public.users
                        SET tenant_id = :new_tid,
                            is_active = TRUE
                        WHERE id = :uid
                    """),
                    {"new_tid": tenant_id, "uid": user_id},
                )
                logger.info(
                    "  public.users: %s を tenant_id=%d → %d に付け替え (id=%d)",
                    REVIEW_EMAIL, current_tenant_id, tenant_id, user_id,
                )
            else:
                await conn.execute(
                    text("UPDATE public.users SET is_active = TRUE WHERE id = :uid"),
                    {"uid": user_id},
                )
                logger.info("  public.users: 既存ユーザー (id=%d) is_active=TRUE 確認", user_id)
        else:
            row = (await conn.execute(
                text("""
                    INSERT INTO public.users (
                        tenant_id, username, email, full_name, role, is_active
                    )
                    VALUES (:tid, :username, :email, :fullname, 'user', TRUE)
                    RETURNING id
                """),
                {
                    "tid": tenant_id,
                    "username": REVIEW_DISPLAY_NAME,
                    "email": REVIEW_EMAIL,
                    "fullname": REVIEW_DISPLAY_NAME,
                },
            )).first()
            user_id = int(row[0])
            logger.info("  public.users: 新規作成 %s (id=%d)", REVIEW_EMAIL, user_id)

        if password_hash is not None:
            # 自社ログインのパスワード（ADR-1013）。password_changed_at を進めると更新用トークンが切れる
            await conn.execute(
                text("""
                    UPDATE public.users
                    SET password_argon2_hash = :h,
                        password_changed_at = :at,
                        failed_login_count = 0,
                        locked_until = NULL
                    WHERE id = :uid
                """),
                {"h": password_hash, "at": datetime.now(timezone.utc).replace(microsecond=0), "uid": user_id},
            )
            logger.info("  public.users: パスワードを設定 (id=%d)", user_id)

        # 新テナントのロール取得 + staff 作成
        role_id = await _resolve_role_id(conn, tenant_id, schema_name, "オーナー")
        await conn.execute(
            text("INSERT INTO user_roles (user_id, role_id) VALUES (:uid, :rid) ON CONFLICT DO NOTHING"),
            {"uid": user_id, "rid": role_id},
        )
        logger.info("  user_roles: オーナーロール付与")

        await _create_staff_record(
            conn,
            tenant_id=tenant_id,
            user_id=user_id,
            email=REVIEW_EMAIL,
            display_name=REVIEW_DISPLAY_NAME,
            role_id=role_id,
        )

    return user_id


# ---------------------------------------------------------------------------
# 結果出力
# ---------------------------------------------------------------------------

def _write_result_file(tenant_id: int, new_password: str | None) -> Path:
    """セットアップ結果を /tmp に書き出す。

    new_password が None の場合（パスワード未変更）は "unchanged" と記載。
    パスワード本文はこのファイル以外に出力しない。
    """
    schema_name = f"tenant_{tenant_id:03d}"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = Path("/tmp") / f"review_tenant_setup_{stamp}.txt"

    if new_password is not None:
        password_line = f"password : {new_password}"
        reset_note = "パスワードリセット: 実行済み (ALLOW_REVIEW_TENANT_PASSWORD_RESET=1)"
    else:
        password_line = "password : unchanged（既存パスワードを維持）"
        reset_note = (
            "パスワードリセット: スキップ（既存ユーザーのため変更なし）\n"
            "  変更が必要な場合: ALLOW_REVIEW_TENANT_PASSWORD_RESET=1 を追加して再実行"
        )

    content = f"""=== ADR-028: tenant-review セットアップ結果 ===

テナント情報:
  tenant_code : {TENANT_CODE}
  tenant_name : {TENANT_NAME}
  tenant_id   : {tenant_id}
  schema_name : {schema_name}

ログイン情報:
  email    : {REVIEW_EMAIL}
  {password_line}

{reset_note}

次のステップ（手動実施）:
  1. ブラウザで https://app.salesanchor.jp/ にアクセス
  2. 上記 email / password でログイン
  3. Dashboard に Demo データのみ表示されることを確認（AC-1, AC-2）
  4. Meta Inbox → 接続 から OAuth 再接続を実施（AC-4）
     - HIGH LIFE JPN Test Page と treasureislandjapan を紐付ける
  5. Messenger / Instagram で実際にメッセージ送受信を確認（AC-4, AC-5）

注意:
  このファイルはコンテナ再起動で消えます。Shingo に安全な手段で共有してください。
  ChatGPT / PR 本文 / GitHub コメントにパスワードを書かないこと。
"""
    out_path.write_text(content, encoding="utf-8")
    try:
        os.chmod(out_path, 0o600)
    except OSError:
        pass
    return out_path


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------

async def main() -> None:
    from app.auth.utils import generate_password
    from app.auth.passwords import hash_password

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL が未設定です。")
        sys.exit(1)
    if db_url.startswith("postgresql://"):
        db_url = "postgresql+asyncpg://" + db_url[len("postgresql://"):]

    engine = create_async_engine(db_url, echo=False)
    reset_password = _password_reset_requested()

    try:
        logger.info("=== ADR-028: tenant-review セットアップ開始 ===")
        if reset_password:
            logger.warning(
                "ALLOW_REVIEW_TENANT_PASSWORD_RESET=1 検出:"
                " パスワードをリセットします (email=%s)", REVIEW_EMAIL
            )
        else:
            logger.info(
                "通常モード: 既存ユーザーのパスワードは変更しません。"
                " パスワードリセットが必要な場合は ALLOW_REVIEW_TENANT_PASSWORD_RESET=1 を付けて再実行してください。"
            )

        # 1. テナント作成（冪等）
        tenant_id = await _ensure_tenant(engine)

        # 2. スキーマ適用（冪等）
        await _apply_tenant_schema(engine, tenant_id)

        # 3. パスワード準備（新しく作るとき・パスワードが無いとき・リセット指定のときだけ）
        new_password: str | None = None
        password_hash: str | None = None
        has_password = await _has_password(engine)
        if _should_write_password(has_password, reset_password):
            new_password = generate_password()
            password_hash = hash_password(new_password)
        else:
            logger.info("既存ユーザーのため password update skipped (email=%s)", REVIEW_EMAIL)

        # 4. DB ユーザー登録・テナント付け替え・パスワード設定（冪等）
        await _setup_user(engine, tenant_id, password_hash)

        # 5. Demo データシード
        # ADR-089: customers テーブルは廃止済み（2026-06-01 DROP）。
        # Demo データは scripts/qa/seed-tenant.sql（QA Smoke Suite）で管理。
        logger.info(
            "Demo データシード: スキップ"
            " (ADR-089: customers テーブル廃止済み。Demo データは scripts/qa/seed-tenant.sql を参照)"
        )

        # 6. 結果ファイル出力
        out_path = _write_result_file(tenant_id, new_password)

        logger.info("\n=== セットアップ完了 ===")
        logger.info("結果ファイル: %s", out_path)
        if new_password is not None:
            logger.info(
                "パスワードリセット済み。結果ファイルを Shingo に安全な手段で共有してください。"
            )
            logger.info(
                "取り出し（VPS で実行）: docker compose exec -T backend cat %s", out_path
            )
        else:
            logger.info("パスワードは変更されていません。既存パスワードでそのままログインできます。")

    finally:
        await engine.dispose()


if __name__ == "__main__":
    _check_guard()
    asyncio.run(main())
