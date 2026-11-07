"""U2: 登録されたサーバーにボットが入っているかを、読むだけで確かめる。

設計: docs/handoff/discord-guild-membership-check/design.md 4-1。
backend の入れ物の中で `python -` として標準入力から流す（scripts/ops/discord-guild-membership-check.sh）。
DB は読み取り専用の1本の SELECT だけ。Discord は GET だけ。
出力にサーバーの番号・名前・ボットの鍵・例外の本文は出さない。
"""
import asyncio
import os
import re
import sys

PAGE_LIMIT = 200
MAX_PAGES = 50


class CheckFailure(Exception):
    """決められた5種の失敗の印を運ぶ。本文は出さない。"""

    def __init__(self, mark: str) -> None:
        super().__init__(mark)
        self.mark = mark


def judge(rows, bot_ids):
    """rows = (tenant_id, purpose, guild_id)。出力の行（先頭2行と末尾1行を含む）を返す。"""
    registered = set()
    lines = [
        "bot_guild_count=%d" % len(bot_ids),
        "config_rows=%d" % len(rows),
    ]
    for tenant_id, purpose, guild_id in rows:
        gid = str(guild_id).strip()
        registered.add(gid)
        mark = "o" if gid in bot_ids else "x"
        lines.append("tenant=%s purpose=%s bot_in_guild=%s" % (tenant_id, purpose, mark))
    unregistered = len([b for b in bot_ids if b not in registered])
    lines.append("unregistered_bot_guilds=%d" % unregistered)
    return lines


async def fetch_all(request):
    """request(path) は応答の配列を返す非同期関数。after= で続きを取り、200件未満で止める。"""
    guilds = []
    after = None
    for _ in range(MAX_PAGES):
        path = "/users/@me/guilds?limit=%d" % PAGE_LIMIT
        if after is not None:
            path += "&after=%s" % after
        page = await request(path)
        page = page or []
        guilds.extend(page)
        if len(page) < PAGE_LIMIT:
            return guilds
        after = str(page[-1]["id"])
    raise CheckFailure("too_many_pages")


def _self_test():
    # T1: 一致した行が o、もう1行が x、登録に無いボット側が数えられる
    rows = [(1, "customer", "10"), (2, "own", "20")]
    out = judge(rows, {"10", "30", "40"})
    assert out == [
        "bot_guild_count=3",
        "config_rows=2",
        "tenant=1 purpose=customer bot_in_guild=o",
        "tenant=2 purpose=own bot_in_guild=x",
        "unregistered_bot_guilds=2",
    ], out

    # T2: 長い作り物の番号を使っても、出力に 17〜20 桁の数字が出ない
    fake_id = "1" * 18
    out = judge([(3, "customer", fake_id)], {fake_id})
    for line in out:
        assert re.search(r"\d{17,20}", line) is None, line
    assert out[2] == "tenant=3 purpose=customer bot_in_guild=o", out

    # T3: ページ分け。200件・200件・3件で3回止まり、2回目以降に前回最後の id が入る
    pages = [
        [{"id": str(i)} for i in range(1, 201)],
        [{"id": str(i)} for i in range(201, 401)],
        [{"id": str(i)} for i in range(401, 404)],
    ]
    paths = []

    async def fake_request(path):
        paths.append(path)
        return pages[len(paths) - 1]

    got = asyncio.run(fetch_all(fake_request))
    assert len(paths) == 3, paths
    assert len(got) == 403, len(got)
    assert "after=" not in paths[0], paths
    assert paths[1].endswith("&after=200"), paths
    assert paths[2].endswith("&after=400"), paths

    # T4: 登録0行 → 3行だけ
    out = judge([], {"1", "2", "3"})
    assert out == [
        "bot_guild_count=3",
        "config_rows=0",
        "unregistered_bot_guilds=3",
    ], out

    print("self-test ok 4")


async def _main(AsyncSessionLocal, engine, discord_api_request, DiscordAPIError):
    from sqlalchemy import text

    try:
        bot_token = os.environ.get("DISCORD_BOT_TOKEN")
        if not bot_token:
            raise CheckFailure("missing_env")

        try:
            async with AsyncSessionLocal() as session:
                await session.execute(text("SET TRANSACTION READ ONLY"))
                result = await session.execute(
                    text(
                        "SELECT tenant_id, purpose, guild_id "
                        "FROM public.tenant_discord_config ORDER BY tenant_id, purpose"
                    )
                )
                rows = [(r[0], r[1], r[2]) for r in result.all()]
        except Exception:
            raise CheckFailure("db_error")

        async def request(path):
            return await discord_api_request(
                method="GET",
                path=path,
                bot_token=bot_token,
                expected_statuses=(200,),
            )

        try:
            guilds = await fetch_all(request)
        except DiscordAPIError as exc:
            code = exc.status_code
            status = "%03d" % code if isinstance(code, int) else "000"
            raise CheckFailure("discord_error status=%s" % status)

        bot_ids = {str(g["id"]) for g in guilds}
        for line in judge(rows, bot_ids):
            print(line)
        return 0
    except CheckFailure as failure:
        print("error=%s" % failure.mark, file=sys.stderr)
        return 1
    finally:
        await engine.dispose()


def run():
    try:
        import logging
        import warnings

        logging.disable(logging.CRITICAL)
        warnings.simplefilter("ignore")
        from app.database import AsyncSessionLocal, engine

        engine.sync_engine.echo = False
        from app.services.discord_rest import DiscordAPIError, discord_api_request

        return asyncio.run(_main(AsyncSessionLocal, engine, discord_api_request, DiscordAPIError))
    except Exception:
        print("error=unexpected", file=sys.stderr)
        return 1


if __name__ == "__main__":
    if "--self-test" in sys.argv[1:]:
        _self_test()
    else:
        sys.exit(run())
