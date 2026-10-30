#!/usr/bin/env python3
"""初回パスワード発行（ADR-1013 便4b）。

対象: is_active かつ password_argon2_hash が NULL の利用者。
  --apply なし : 対象の件数だけを標準エラーに出す。DB には書かない（取引は取り消す）。
  --apply      : 1 つの取引で 1 人ずつ 20 文字のパスワードを作り、Argon2id で保存する。
                 UPDATE の件数が 1 でない人が 1 人でもいたら全部取り消して終わる
                 （標準出力には何も出さない）。コミットが成功してから
                 「id <TAB> email <TAB> パスワード」を標準出力へ出す。

パスワードの平文は、ログにもファイルにも書かない。標準出力へ出すだけ（K11）。
呼び出し側（PO の Mac）が、標準出力を権限 600 のファイルへ直接受ける。ssh に -t は付けない。

起動（backend コンテナの中。作業場所は /app）:
    python -m scripts.issue_initial_passwords [--apply]

コミットの前に切れたとき: DB は取り消されているので、もう一度 --apply から。
コミットの後に出力の途中で切れたとき: パスワードは DB に入ったが手元に無い。
  2 回目は 0 件になるので、その人たちには再設定メールを送る（「パスワードを忘れた」）。
"""
from __future__ import annotations

import argparse
import asyncio
import os
import secrets
import string
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from app.auth.passwords import hash_password

USERS_TABLE = "public.users"  # 試験では SQLite 用に差し替える
PASSWORD_LENGTH = 20
# タブ・引用符・空白など、TSV やシェルで壊れる文字を使わない
_ALPHABET = string.ascii_letters + string.digits


def generate_password() -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(PASSWORD_LENGTH))


class IssueAborted(Exception):
    """UPDATE の件数が 1 でない人がいた。呼び出し側は取引を取り消すこと。"""


async def issue(
    conn: AsyncConnection, *, apply: bool, operator_context: bool = True
) -> tuple[int, list[tuple[int, str, str]]]:
    """受け取った接続の上で動く。commit も rollback もしない（呼び出し側が行う）。

    戻り値: (対象の件数, apply のときだけ [(id, email, 平文)])。
    operator_context=False は試験用（運営の文脈を設定しない＝RLS で UPDATE が 0 行になる）。
    """
    if operator_context and conn.dialect.name == "postgresql":
        # users の書き込みは RLS が FORCE。運営の文脈が無いと UPDATE が 0 行になる（F22）
        await conn.execute(text("SELECT set_config('app.is_operator', 'true', true)"))
    targets = (
        await conn.execute(
            text(
                f"SELECT id, email FROM {USERS_TABLE} "
                "WHERE is_active AND password_argon2_hash IS NULL ORDER BY id"
            )
        )
    ).all()
    if not apply:
        return len(targets), []

    issued: list[tuple[int, str, str]] = []
    for user_id, email in targets:
        plain = generate_password()
        result = await conn.execute(
            text(
                f"UPDATE {USERS_TABLE} SET password_argon2_hash = :h, "
                "password_changed_at = CURRENT_TIMESTAMP, "
                "failed_login_count = 0, locked_until = NULL "
                "WHERE id = :id AND password_argon2_hash IS NULL"
            ),
            {"h": hash_password(plain), "id": user_id},
        )
        if result.rowcount != 1:
            raise IssueAborted()
        issued.append((user_id, email, plain))
    return len(targets), issued


def _connect_args(url: str) -> dict:
    return {"prepared_statement_cache_size": 0} if url.startswith("postgresql") else {}


async def _run(url: str, apply: bool) -> int:
    engine = create_async_engine(url, echo=False, connect_args=_connect_args(url))
    try:
        async with engine.connect() as conn:
            trans = await conn.begin()
            try:
                count, issued = await issue(conn, apply=apply)
                if not apply:
                    await trans.rollback()
                    print(f"対象 {count} 件（試し実行。書き込みなし）", file=sys.stderr)
                    return 0
                await trans.commit()
            except IssueAborted:
                await trans.rollback()
                print("中止: 更新件数が 1 でない人がいたため全部取り消しました（書き込み 0 件）", file=sys.stderr)
                return 1
            except BaseException:
                if trans.is_active:
                    await trans.rollback()
                raise
    finally:
        await engine.dispose()

    # ここへ来たのはコミット成功後
    print(f"発行 {len(issued)} 件（コミット済み）", file=sys.stderr)
    for user_id, email, plain in issued:
        sys.stdout.write(f"{user_id}\t{email}\t{plain}\n")
    sys.stdout.flush()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.issue_initial_passwords",
        description="is_active かつパスワード未設定の利用者に初回パスワードを発行する。"
        "--apply なしは件数だけを標準エラーに出す。",
    )
    parser.add_argument("--apply", action="store_true", help="実際に発行して保存する（標準出力に id/email/パスワード）")
    args = parser.parse_args(argv)
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL が未設定です", file=sys.stderr)
        return 2
    return asyncio.run(_run(url, args.apply))


if __name__ == "__main__":
    sys.exit(main())
