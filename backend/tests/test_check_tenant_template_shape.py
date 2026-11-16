"""scripts/check_tenant_template_shape.py（段5 5-2・K5-2 の検査の台本）の試験。

- 形の差の取り方・許す一覧（表単位）の動きは DB なしで確かめる。
- 「差 0 なら緑・ひな形が登録と食い違うと赤」は、使い捨ての PostgreSQL（PGHOST・PGPORT・PGUSER・PGPASSWORD）に
  対して、1 本だけの小さな登録で確かめる。つながらないときは飛ばす（CI の tenant-template-shape job は DB がある）。
"""

from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
import uuid
from pathlib import Path

import psycopg2
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load():
    spec = importlib.util.spec_from_file_location("check_tenant_template_shape", REPO_ROOT / "scripts/check_tenant_template_shape.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


chk = _load()


# ───────────────────────── DB なし ─────────────────────────


def test_diff_zero_when_same():
    shape = {"表": {"a": "r|rls=true"}, "列": {"a.id": "integer"}}
    assert chk.diff_shapes(shape, shape, allowed={}) == []


def test_diff_reports_three_kinds():
    before = {"列": {"a.x": "integer", "a.y": "text"}}
    after = {"列": {"a.x": "bigint", "a.z": "text"}}
    got = {(k, n, how) for k, n, how, _b, _a in chk.diff_shapes(before, after, allowed={})}
    assert got == {("列", "a.x", "中身が違う"), ("列", "a.y", "流す前だけ"), ("列", "a.z", "流した後だけ")}


def test_allowed_table_covers_only_that_table_and_marks_used():
    before = {"表": {}, "列": {}, "索引": {}, "制約": {}, "連番": {}, "権限": {}}
    after = {
        "表": {"channel_masters": "r", "other": "r"},
        "列": {"channel_masters.id": "integer", "other.id": "integer"},
        "索引": {"channel_masters_pkey": "channel_masters|CREATE UNIQUE INDEX ...", "other_pkey": "other|CREATE UNIQUE INDEX ..."},
        "制約": {"channel_masters.channel_masters_pkey": "p|PRIMARY KEY (id)"},
        "連番": {"channel_masters_id_seq": "bigint", "other_id_seq": "bigint"},
        "権限": {"r:channel_masters": "{a=r/b}", "S:channel_masters_id_seq": "{a=r/b}", "r:other": "{a=r/b}"},
    }
    used: set[str] = set()
    diffs = chk.diff_shapes(before, after, allowed={"channel_masters": "理由"}, used=used)
    assert used == {"channel_masters"}
    names = {(k, n) for k, n, *_ in diffs}
    assert names == {("表", "other"), ("列", "other.id"), ("索引", "other_pkey"), ("連番", "other_id_seq"), ("権限", "r:other")}


def test_allowed_row_unused_when_no_diff():
    shape = {"表": {"a": "r"}}
    used: set[str] = set()
    assert chk.diff_shapes(shape, shape, allowed={"channel_masters": "理由"}, used=used) == []
    assert used == set()


def test_allowed_tables_is_only_channel_masters():
    # カード 5-2 第3版の決め1: 許す一覧は channel_masters の 1 表だけ。増やすときは PO に聞く。
    assert set(chk.ALLOWED_TABLES) == {"channel_masters"}
    assert "K6" in chk.ALLOWED_TABLES["channel_masters"]


def test_registry_counts_lines_like_runner():
    reg = chk.registry()
    text = (REPO_ROOT / "scripts/run_all_migrations.sh").read_text(encoding="utf-8").splitlines()
    expected = [ln for ln in text if ln.startswith(("run_sql ", "run_sql\t", "run_py ", "run_py\t"))]
    assert len(reg) == len(expected) > 300
    for _line, _kind, target, _extra in reg:
        assert (REPO_ROOT / target).is_file(), target


def test_excluded_registry_files_exist_and_are_registered():
    registered = {t for _l, _k, t, _e in chk.registry()}
    for target in chk.EXCLUDED_REGISTRY:
        assert target in registered, target
        assert (REPO_ROOT / target).is_file(), target


def test_template_does_not_contain_channel_masters():
    from app.services import tenant as tenant_service

    for name in ("_TENANT_TABLES_SQL", "_RLS_ENABLE_SQL", "_RLS_POLICY_SQL"):
        assert "channel_masters" not in getattr(tenant_service, name), name


# ───────────────────────── DB あり ─────────────────────────


def _db_reachable() -> bool:
    try:
        c = psycopg2.connect(**chk._env_conn("postgres"), connect_timeout=3)
        c.close()
        return True
    except Exception:
        return False


needs_db = pytest.mark.skipif(not _db_reachable(), reason="使い捨ての PostgreSQL につながらない")


def _run_with_one_migration(tmp_path, template_extra_sql: str, monkeypatch) -> tuple[list, str]:
    """会社を作り（ひな形に template_extra_sql を足して）、列を 1 つ足す小さな移行 1 本を流して、差を返す。"""
    from app.services import tenant as tenant_service

    if template_extra_sql:
        monkeypatch.setattr(tenant_service, "_TENANT_TABLES_SQL", tenant_service._TENANT_TABLES_SQL + "\n" + template_extra_sql)

    mig = tmp_path / "add_probe_column.sql"
    mig.write_text(
        "DO $$\nDECLARE s text;\nBEGIN\n"
        "  FOR s IN SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'tenant\\_%' LOOP\n"
        "    EXECUTE format('ALTER TABLE %I.leads ADD COLUMN IF NOT EXISTS zz_probe integer', s);\n"
        "  END LOOP;\nEND $$;\n",
        encoding="utf-8",
    )
    db = "shape_t_" + uuid.uuid4().hex[:8]
    chk.ensure_app_role()
    chk.create_database(db)
    schema = asyncio.run(chk.prepare_public_and_tenant(db))
    assert schema == chk.SCHEMA
    conn = psycopg2.connect(**chk._env_conn(db))
    try:
        before = chk.take_shape(conn)
        results = chk.run_registry(db, reg=[(1, "sql", str(mig), "")])
        after = chk.take_shape(conn)
    finally:
        conn.close()
    assert [r[3] for r in results] == [0]
    return chk.diff_shapes(before, after), db


@needs_db
def test_shape_diff_zero_when_template_matches_registry(tmp_path, monkeypatch):
    extra = "ALTER TABLE {schema}.leads ADD COLUMN IF NOT EXISTS zz_probe integer;"
    diffs, _db = _run_with_one_migration(tmp_path, extra, monkeypatch)
    assert diffs == []


@needs_db
def test_shape_diff_red_when_registry_adds_column_template_lacks(tmp_path, monkeypatch):
    diffs, _db = _run_with_one_migration(tmp_path, "", monkeypatch)
    assert [(k, n, how) for k, n, how, _b, _a in diffs] == [("列", "leads.zz_probe", "流した後だけ")]
