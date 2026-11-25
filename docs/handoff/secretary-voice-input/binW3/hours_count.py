"""本番の予定の始まりの時（日本時間）ごとの件数を数える。読むだけ（READ ONLY の取引）。中身（題名など）は出さない。"""
import asyncio, os
import asyncpg

async def main():
    url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
    con = await asyncpg.connect(url)
    try:
        async with con.transaction(readonly=True):
            schemas = [r["table_schema"] for r in await con.fetch(
                "SELECT table_schema FROM information_schema.tables WHERE table_name='calendar_events' ORDER BY 1")]
            print("schemas", len(schemas))
            total = {}
            for s in schemas:
                rows = await con.fetch(
                    f'SELECT source, EXTRACT(HOUR FROM start_datetime AT TIME ZONE \'Asia/Tokyo\')::int AS h, count(*) AS n '
                    f'FROM "{s}".calendar_events WHERE is_all_day IS NOT TRUE GROUP BY 1,2')
                n_all = await con.fetchval(f'SELECT count(*) FROM "{s}".calendar_events')
                n_day = await con.fetchval(f'SELECT count(*) FROM "{s}".calendar_events WHERE is_all_day IS TRUE')
                print("schema_rows", s[:3] + "***", n_all, "all_day", n_day)
                for r in rows:
                    k = (r["source"], r["h"])
                    total[k] = total.get(k, 0) + r["n"]
            for (src, h), n in sorted(total.items(), key=lambda x: (str(x[0][0]), x[0][1] if x[0][1] is not None else -1)):
                print("hour", src, h, n)
    finally:
        await con.close()

asyncio.run(main())
