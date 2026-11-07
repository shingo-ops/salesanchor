"""U2: 登録されたサーバーにボットが入っているかを、読むだけで確かめる。

設計: docs/handoff/discord-guild-membership-check/design.md 4-1。
backend の入れ物の中で `python -` として標準入力から流す（scripts/ops/discord-guild-membership-check.sh）。
DB は読み取り専用の1本の SELECT だけ。Discord は GET だけ。
出力にサーバーの番号・名前・ボットの鍵・例外の本文は出さない。
例外: 旗 --show-unregistered-names があるときだけ、登録に無いボットのサーバーの名前を出す
（design.md 14。番号・鍵・登録済みのサーバーの名前は出ない。DB は読み取り専用の SELECT が2本）。
"""
import asyncio
import os
import re
import sys
import unicodedata

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


def clean_name(name):
    """名前を1行に収める。"""
    # (1) 文字列でない値
    if not isinstance(name, str):
        return "(no_name)"
    # (2) 制御文字・書式文字（種類 C*）と行・段落の区切り（Zl・Zp）を消す
    kept = []
    for ch in name:
        cat = unicodedata.category(ch)
        if cat.startswith("C") or cat in ("Zl", "Zp"):
            continue
        kept.append(ch)
    text = "".join(kept)
    # (3) 17桁以上の数字の並びを # に置き換える
    text = re.sub(r"\d{17,}", "#", text)
    # (4) 前後の空白を除き、100文字で切る
    text = text.strip()
    if len(text) > 100:
        text = text[:100] + "~"
    # (5) 空なら
    return text or "(no_name)"


def unregistered_lines(rows, guilds, viewer_ids):
    """登録に無いボットのサーバーだけを `unregistered name=<名前> is_viewer_guild=<o|x>` の形で返す。

    rows = (tenant_id, purpose, guild_id)。guilds = 応答の要素（id と name）。
    viewer_ids = 閲覧ページの申し込み用サーバーの番号の集合（strip 済みの文字列）。
    id で重複を除き、先に出たほうの名前を残す。並びは clean_name の文字の順（同じ名前なら出る順）。
    """
    registered = {str(r[2]).strip() for r in rows}
    seen = set()
    picked = []
    for g in guilds:
        gid = str(g["id"])
        if gid in seen:
            continue
        seen.add(gid)
        if gid in registered:
            continue
        picked.append((clean_name(g.get("name")), "o" if gid in viewer_ids else "x"))
    picked.sort(key=lambda item: item[0])
    return ["unregistered name=%s is_viewer_guild=%s" % (n, mark) for n, mark in picked]


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

    # T5: 登録2行・ボット側4件（登録済み2・viewer 1・その他1）→ 登録に無い2行だけ、名前の順
    rows = [(1, "customer", "10"), (2, "own", " 20 ")]
    guilds = [
        {"id": "10", "name": "Registered One"},
        {"id": "30", "name": "Zeta Fake"},
        {"id": "20", "name": "Registered Two"},
        {"id": "40", "name": "Alpha Fake"},
        {"id": "40", "name": "Alpha Dup"},
    ]
    out = unregistered_lines(rows, guilds, {"30"})
    assert out == [
        "unregistered name=Alpha Fake is_viewer_guild=x",
        "unregistered name=Zeta Fake is_viewer_guild=o",
    ], out

    # T6: clean_name
    messy = (
        "A\nB\tC​D E F"
        + "1" * 18
        + "123456789​123456789"
        + "z" * 150
    )
    cleaned = clean_name(messy)
    for ch in cleaned:
        cat = unicodedata.category(ch)
        assert not cat.startswith("C") and cat not in ("Zl", "Zp"), repr(ch)
    assert re.search(r"\d{17,20}", cleaned) is None, cleaned
    assert len(cleaned) <= 101, len(cleaned)
    assert clean_name("a" * 150) == "a" * 100 + "~"
    assert clean_name("1" * 18) == "#"
    assert clean_name("123456789​123456789") == "#"
    assert clean_name(None) == "(no_name)"
    assert clean_name("​\n") == "(no_name)"

    print("self-test ok 6")


async def _main(AsyncSessionLocal, engine, discord_api_request, DiscordAPIError, show_names=False):
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
                viewer_ids = set()
                if show_names:
                    viewer_result = await session.execute(
                        text("SELECT guild_id FROM public.viewer_discord_config")
                    )
                    viewer_ids = {str(r[0]).strip() for r in viewer_result.all()}
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
        if show_names:
            for line in unregistered_lines(rows, guilds, viewer_ids):
                print(line)
        return 0
    except CheckFailure as failure:
        print("error=%s" % failure.mark, file=sys.stderr)
        return 1
    finally:
        await engine.dispose()


def run(show_names=False):
    try:
        import logging
        import warnings

        logging.disable(logging.CRITICAL)
        warnings.simplefilter("ignore")
        from app.database import AsyncSessionLocal, engine

        engine.sync_engine.echo = False
        from app.services.discord_rest import DiscordAPIError, discord_api_request

        return asyncio.run(
            _main(AsyncSessionLocal, engine, discord_api_request, DiscordAPIError, show_names)
        )
    except Exception:
        print("error=unexpected", file=sys.stderr)
        return 1


if __name__ == "__main__":
    _args = sys.argv[1:]
    if "--self-test" in _args:
        _self_test()
    elif all(a == "--show-unregistered-names" for a in _args):
        sys.exit(run("--show-unregistered-names" in _args))
    else:
        print("error=unexpected", file=sys.stderr)
        sys.exit(1)
