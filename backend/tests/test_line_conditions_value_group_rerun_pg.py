"""line_conditions.value_group の CHECK を migration 再実行で狭め直さないことの確認（CI の使い捨て PG）。

run_all_migrations.sh は毎回全 migration を流す。19（promo_pack/single）と 20（booklet）を
2回目に流しても、booklet の行がある本番で失敗しないこと。
pg fixture は CI の使い捨て DB を作って消す（test_tcg_work_matching_integration.py）。
"""
from pathlib import Path

from tests.test_super_admin_viewers import needs_ci_pg
from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture

ROOT = Path(__file__).resolve().parents[2]
M19 = ROOT / "migrations/20261019_100000_line_conditions_value_group_add_promo_single.sql"
M20 = ROOT / "migrations/20261020_100000_line_conditions_value_group_add_booklet.sql"
DEF_SQL = (
    "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
    "WHERE conrelid='public.line_conditions'::regclass AND conname='line_conditions_value_group_check'"
)


def _def(cur) -> str:
    cur.execute(DEF_SQL)
    return cur.fetchone()[0]


@needs_ci_pg
def test_widens_then_rerun_keeps_booklet(pg):  # noqa: F811
    conn, _, _ = pg
    cur = conn.cursor()
    cur.execute("SELECT to_regclass('public.line_conditions') IS NULL")
    assert cur.fetchone()[0], "使い捨て DB には line_conditions が無いはず"
    cur.execute(
        "CREATE TABLE public.line_conditions (id serial PRIMARY KEY, value_group text);"
        "ALTER TABLE public.line_conditions ADD CONSTRAINT line_conditions_value_group_check "
        "CHECK (value_group IS NULL OR value_group IN ('box','case','pack'))"
    )
    # K2: box/case/pack だけの状態から 19 を流すと広がる
    cur.execute(M19.read_text())
    d = _def(cur)
    assert "'promo_pack'" in d and "'single'" in d
    cur.execute(M20.read_text())
    assert "'booklet'" in _def(cur)
    cur.execute("INSERT INTO public.line_conditions (value_group) VALUES ('booklet')")
    # K1: 19 → 20 の再実行がエラー0で、booklet が残る
    cur.execute(M19.read_text())
    cur.execute(M20.read_text())
    assert "'booklet'" in _def(cur)
    cur.execute("SELECT count(*) FROM public.line_conditions WHERE value_group='booklet'")
    assert cur.fetchone()[0] == 1
