"""Python の移行を動かす入口（ADR-1037 の拡張・段1）。

scripts/run_all_migrations.sh の run_py は、本物の移行を直接ではなくこの入口経由で動かす。
環境変数 MIGRATION_LOCK_TIMEOUT が空でないときだけ、sqlalchemy.ext.asyncio.create_async_engine を
差し替え、接続ごとの server_settings に lock_timeout と application_name を足す。
移行本体は触らない。値が無いときは何も差し替えない（手で流すときは今までと同じ）。

差し替えは暗黙なので、終了時に差し替えた回数を標準エラーへ必ず1行出す。
前提: 呼び先は全部 `from sqlalchemy.ext.asyncio import create_async_engine` の形で取り込む
（from-import は取り込み時点の属性を読むため）。この前提は migration-test の S1 が見張る。

使い方: python scripts/migration_py_entry.py scripts/xxx.py [引数...]
"""
import os
import runpy
import sys

APP_NAME = "salesanchor_migration"


def main() -> int:
    if len(sys.argv) < 2:
        sys.stderr.write("usage: migration_py_entry.py <script> [args...]\n")
        return 2

    target = sys.argv[1]
    timeout = os.environ.get("MIGRATION_LOCK_TIMEOUT", "")
    applied = 0

    if timeout:
        import sqlalchemy.ext.asyncio as sa_asyncio

        original = sa_asyncio.create_async_engine

        def patched(*args, **kwargs):
            nonlocal applied
            connect_args = dict(kwargs.get("connect_args") or {})
            server_settings = dict(connect_args.get("server_settings") or {})
            server_settings["lock_timeout"] = timeout
            server_settings.setdefault("application_name", APP_NAME)
            connect_args["server_settings"] = server_settings
            kwargs["connect_args"] = connect_args
            applied += 1
            return original(*args, **kwargs)

        sa_asyncio.create_async_engine = patched

    # 本物を直接動かしたときと同じ sys.argv にする（sys.path[0] は入口と同じ scripts/）
    sys.argv = [target, *sys.argv[2:]]
    try:
        runpy.run_path(target, run_name="__main__")
    finally:
        shown = timeout if timeout else "unset"
        sys.stderr.write(
            f"migration_py_entry: lock_timeout={shown} applied to {applied} engine(s)\n"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
