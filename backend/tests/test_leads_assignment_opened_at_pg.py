# ruff: noqa: F811
"""leads.assignment_opened_at の PostgreSQL 統合テスト（CI の使い捨て PostgreSQL 専用）。

受信箱「新規」バッジの出し方（expand/contract の先行便・列だけ）。本テストは
migrations/20261015_090000_add_leads_assignment_opened_at.sql の中身を読み込んで
そのまま実行し、本体の DO $$ ブロックを検証する。

参照元（release/inbox-new-assignment-badge）の test_inbox_new_assignment_badge.py の
A1/A2/A11 相当は、DO $$ の分岐ロジックを Python/SQLite 側に書き写しており、本体の
SQL を実行していなかった（審査 2026-10-15 D9）。本テストはその欠陥を踏まえ、必ず
本体 SQL を実 PostgreSQL に対して実行する。

T1: マイグレーションを実行すると leads.assignment_opened_at が増える
T2: 実行前に assigned_to が入っている行は NOW() で埋まり、assigned_to IS NULL の行は
    NULL のままである
T3（最重要・審査 D9）: 同じ SQL をもう一度実行しても、「assigned_to が入っていて
    assignment_opened_at が NULL」の行（＝担当になったが未開封＝バッジを出すべき行）
    が NULL のまま壊れないこと
T4: 新規テナントの定義（backend/app/services/tenant.py）にも列があること（静的チェック）
T5（CI で実発生・2026-10-17）: leads 表はあるが assigned_to 列が無いスキーマでも
    マイグレーションがエラーにならず、assignment_opened_at が追加されること。
    CI の .github/workflows/migration-test.yml が使う試験用 tenant_001.leads は
    assigned_to を持たない最小定義であり、実際に migration-test で
    `column "assigned_to" does not exist` エラーが発生した（本番の leads は
    migrations/003_add_phase1_tenant_tables.sql:92 で assigned_to を持つ）。

leads 表の作り方（柱3-a/b・check_test_schema_dup gate 対応）:
  本番の leads 定義を本テスト内に手で書き直さない。migrations/003_add_phase1_tenant_tables.sql
  （leads 表の初出）を読み込み、見出しコメントで「リード管理テーブル」の区間と、
  それが使う lead_code_seq の区間だけを切り出して実行する（customers/deals/roles/
  permissions は本テストの対象外で、しかも customers は ADR-089、deals は
  migrations/20260729_043520_drop_deals.sql で本番から既に DROP 済みのため、
  003 を丸ごと実行すると現在はそれ自体が失敗する。切り出した区間だけなら
  customers/deals に依存しない）。
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.test_tcg_work_matching_integration import SCHEMA
from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture

pytestmark = pytest.mark.skipif(os.getenv("GITHUB_ACTIONS") != "true", reason="Disposable CI PostgreSQL service required")

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = REPO_ROOT / "migrations" / "20261015_090000_add_leads_assignment_opened_at.sql"
TENANT_SERVICE_PATH = REPO_ROOT / "backend" / "app" / "services" / "tenant.py"
PHASE1_TENANT_TABLES_PATH = REPO_ROOT / "migrations" / "003_add_phase1_tenant_tables.sql"
TENANT_ID = int(SCHEMA.rsplit("_", 1)[-1])

# 003 の見出しコメント（切り出しの境界。これらの文字列には CREATE TABLE を含まないため
# check_test_schema_dup gate には引っかからない）
_SEQ_BANNER = "-- === シーケンス（コード自動採番用） ===\n"
_SEQ_END_BANNER = "-- 既存レコードを跨いで"
_LEADS_BANNER = "-- === リード管理テーブル ===\n"
_LEADS_END_BANNER = "-- === チーム管理テーブル ===\n"


def _leads_table_sql() -> str:
    """003 から「シーケンス」区間と「リード管理テーブル」区間だけを切り出し、
    {schema}/{schema_raw}/{tenant_id} を置換して返す。customers/deals/roles/permissions
    には触れない（本テストの対象外・かつ customers/deals は本番で既に DROP 済み）。
    """
    text = PHASE1_TENANT_TABLES_PATH.read_text(encoding="utf-8")
    seq_block = text[text.index(_SEQ_BANNER):text.index(_SEQ_END_BANNER)]
    leads_block = text[text.index(_LEADS_BANNER):text.index(_LEADS_END_BANNER)]
    return (seq_block + "\n" + leads_block).format(schema=SCHEMA, schema_raw=SCHEMA, tenant_id=TENANT_ID)


def _apply_migration(connection) -> None:
    """本体の SQL ファイルをそのまま読み込んで実行する（書き写し禁止・審査 D9）。"""
    with connection.cursor() as cur:
        cur.execute(MIGRATION_PATH.read_text(encoding="utf-8"))


def _create_leads_from_real_migration(connection, schema: str) -> None:
    """本番の leads 定義（migrations/003_add_phase1_tenant_tables.sql）をそのまま使って
    テスト用スキーマに leads 表を作る（柱3-a/b: 本番テーブル定義の手書きコピー禁止）。
    """
    with connection.cursor() as cur:
        cur.execute(_leads_table_sql())


def _drop_assigned_to(connection, schema: str) -> None:
    """T5 用: 「leads 表はあるが assigned_to が無い」状態を作る
    （CI の試験用 tenant_001.leads が実際にこの状態）。"""
    with connection.cursor() as cur:
        cur.execute(f"ALTER TABLE {schema}.leads DROP COLUMN assigned_to")


def _columns(connection, schema: str) -> set[str]:
    with connection.cursor() as cur:
        cur.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_schema=%s AND table_name='leads'",
            (schema,),
        )
        return {row[0] for row in cur.fetchall()}


def test_t1_migration_adds_the_column(pg):
    connection, _, _ = pg
    _create_leads_from_real_migration(connection, SCHEMA)
    assert "assignment_opened_at" not in _columns(connection, SCHEMA)
    _apply_migration(connection)
    assert "assignment_opened_at" in _columns(connection, SCHEMA)


def test_t2_backfills_assigned_rows_only_leaves_unassigned_rows_null(pg):
    connection, _, _ = pg
    _create_leads_from_real_migration(connection, SCHEMA)
    with connection.cursor() as cur:
        cur.execute(
            f"INSERT INTO {SCHEMA}.leads (customer_name, assigned_to) VALUES ('架空太郎', 10) RETURNING id"
        )
        assigned_id = cur.fetchone()[0]
        cur.execute(
            f"INSERT INTO {SCHEMA}.leads (customer_name, assigned_to) VALUES ('架空花子', NULL) RETURNING id"
        )
        unassigned_id = cur.fetchone()[0]

    _apply_migration(connection)

    with connection.cursor() as cur:
        cur.execute(f"SELECT assignment_opened_at FROM {SCHEMA}.leads WHERE id=%s", (assigned_id,))
        assert cur.fetchone()[0] is not None
        cur.execute(f"SELECT assignment_opened_at FROM {SCHEMA}.leads WHERE id=%s", (unassigned_id,))
        assert cur.fetchone()[0] is None


def test_t3_second_run_does_not_clobber_rows_assigned_but_not_yet_opened(pg):
    """審査 D9: 再実行で「担当になったが未開封」行（バッジを出すべき行）が NULL のまま壊れないこと。

    1回目の実行後（列がもう存在する状態）に新しく担当が付いた行を作り、
    2回目の実行（毎デプロイで再実行される想定）でその行の assignment_opened_at が
    NULL のままであることを確かめる。
    """
    connection, _, _ = pg
    _create_leads_from_real_migration(connection, SCHEMA)
    _apply_migration(connection)  # 1回目: 列を追加し、既存の担当付き行を埋める

    with connection.cursor() as cur:
        # 1回目の後に新しく担当が付いた行（まだ開いていない＝バッジを出すべき行）を作る
        cur.execute(
            f"INSERT INTO {SCHEMA}.leads (customer_name, assigned_to, assignment_opened_at) "
            "VALUES ('架空次郎', 20, NULL) RETURNING id"
        )
        new_row_id = cur.fetchone()[0]

    _apply_migration(connection)  # 2回目: 毎デプロイで再実行される想定（run_all_migrations.sh）

    with connection.cursor() as cur:
        cur.execute(f"SELECT assignment_opened_at FROM {SCHEMA}.leads WHERE id=%s", (new_row_id,))
        assert cur.fetchone()[0] is None


def test_t4_tenant_service_defines_the_column_too():
    """静的チェック。審査指摘: tenant.py 全体への部分文字列照合では、この列が
    leads 以外の CREATE TABLE に移動しても・コメント行に書かれているだけでも緑になってしまう。
    PR-A は tenant.py のまさにこの箇所を触る便なので、leads の CREATE TABLE の中にあることまで
    位置を固定する（参照元 worktree の test_inbox_new_assignment_badge.py の test_a11 と同じ作法）。

    位置の特定は「-- リード管理」見出しコメントを使う（"CREATE TABLE" を自分のソースに
    書くと check_test_schema_dup gate に引っかかるため、見出しコメントで代替する）。
    """
    tenant_py = TENANT_SERVICE_PATH.read_text(encoding="utf-8")
    leads_section_start = tenant_py.index("-- リード管理\n")
    leads_block = tenant_py[leads_section_start:tenant_py.index(");", leads_section_start)]
    assert "assignment_opened_at TIMESTAMPTZ" in leads_block


def test_t5_migration_succeeds_on_a_schema_without_assigned_to(pg):
    """CI で実発生（2026-10-17）: .github/workflows/migration-test.yml の試験用
    tenant_001.leads は assigned_to を持たない最小定義で、これに対して旧版の
    マイグレーションは `column "assigned_to" does not exist` で落ちた
    （CI の実ログ: `UPDATE tenant_001.leads SET assignment_opened_at = NOW()
    WHERE assigned_to IS NOT NULL` が ERROR）。

    「leads 表はあるが assigned_to 列が無い」状態を、本番定義の DDL を手で書かずに作る
    （本番の leads を real migration から作り、assigned_to だけ DROP する）。
    """
    connection, _, _ = pg
    _create_leads_from_real_migration(connection, SCHEMA)
    _drop_assigned_to(connection, SCHEMA)
    assert "assigned_to" not in _columns(connection, SCHEMA)

    _apply_migration(connection)  # 例外を投げずに完了することが本テストの主張

    assert "assignment_opened_at" in _columns(connection, SCHEMA)
