"""line_conditions.value_group の CHECK を migration 再実行で狭め直さないことの確認（CI の使い捨て PG）。

run_all_migrations.sh は毎回全 migration を流す。19（promo_pack/single）と 20（booklet）・20_110000（supply）を
2回目に流しても、booklet・supply の行がある本番で失敗しないこと。
pg fixture は CI の使い捨て DB を作って消す（test_tcg_work_matching_integration.py）。
"""
from pathlib import Path

from tests.test_super_admin_viewers import needs_ci_pg
from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture

ROOT = Path(__file__).resolve().parents[2]
M_RANK = ROOT / "migrations/20261017_120000_line_conditions_value_rank.sql"
M19 = ROOT / "migrations/20261019_100000_line_conditions_value_group_add_promo_single.sql"
M20 = ROOT / "migrations/20261020_100000_line_conditions_value_group_add_booklet.sql"
M21 = ROOT / "migrations/20261020_110000_line_conditions_value_group_add_supply.sql"
DEF_SQL = (
    "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
    "WHERE conrelid='public.line_conditions'::regclass AND conname='line_conditions_value_group_check'"
)


def _def(cur) -> str:
    cur.execute(DEF_SQL)
    return cur.fetchone()[0]


@needs_ci_pg
def test_widens_then_rerun_keeps_booklet_and_supply(pg):  # noqa: F811
    conn, _, _ = pg
    cur = conn.cursor()
    # pg fixture は 20260919_020000 で public.conditions（TABLE）を作り、試験用 helper が
    # conditions_value_group_check を足している。本番と同じ経路（20260922_080000 で line_conditions へ
    # 名前替え → 20261017_120000 で value_group の CHECK）にするため、helper 由来の制約だけ先に外す。
    cur.execute("SELECT to_regclass('public.line_conditions') IS NULL")
    assert cur.fetchone()[0], "使い捨て DB には line_conditions が無いはず"
    cur.execute("ALTER TABLE public.conditions DROP CONSTRAINT conditions_value_group_check")
    # 20260922_080000:71-72 と同じ1文。fixture DB には line_units 等が既にあり migration 全体は流せないため。
    # 後方互換の view（同 :81-83）は今回の検証に不要なので作らない。
    cur.execute("ALTER TABLE public.conditions RENAME TO line_conditions")
    cur.execute(M_RANK.read_text())
    cur.execute(
        "SELECT table_type FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='line_conditions'"
    )
    assert cur.fetchone()[0] == "BASE TABLE"
    d0 = _def(cur)
    assert "'box'" in d0 and "'pack'" in d0 and "'single'" not in d0 and "'booklet'" not in d0
    # K2: box/case/pack だけの状態から 19 を流すと広がる
    cur.execute(M19.read_text())
    d = _def(cur)
    assert "'promo_pack'" in d and "'single'" in d
    cur.execute(M20.read_text())
    assert "'booklet'" in _def(cur) and "'supply'" not in _def(cur)
    cur.execute(M21.read_text())
    assert "'booklet'" in _def(cur) and "'supply'" in _def(cur)
    cur.execute("INSERT INTO public.line_conditions (code, canonical, value_group) VALUES ('ZZ9999', 'rerun-test booklet', 'booklet')")
    # K1: 19 → 20 の再実行がエラー0で、booklet が残る
    cur.execute(M19.read_text())
    cur.execute(M20.read_text())
    assert "'booklet'" in _def(cur)
    cur.execute("SELECT count(*) FROM public.line_conditions WHERE value_group='booklet'")
    assert cur.fetchone()[0] == 1
    # ADR-1035 追補: 19 → 20 → 21 の再実行がエラー0で、booklet・supply の行が残る
    cur.execute("INSERT INTO public.line_conditions (code, canonical, value_group) VALUES ('ZZ9998', 'rerun-test supply', 'supply')")
    cur.execute(M19.read_text())
    cur.execute(M20.read_text())
    cur.execute(M21.read_text())
    d2 = _def(cur)
    assert "'booklet'" in d2 and "'supply'" in d2
    cur.execute("SELECT count(*) FROM public.line_conditions WHERE value_group='supply'")
    assert cur.fetchone()[0] == 1
    cur.execute("SELECT count(*) FROM public.line_conditions WHERE value_group='booklet'")
    assert cur.fetchone()[0] == 1
